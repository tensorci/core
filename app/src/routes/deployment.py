import os
from slugify import slugify
from flask_restplus import Resource, fields
from flask import request, Response, stream_with_context
from src.helpers import utcnow_to_ts
from src.routes import namespace, api
from src.models import Provider, Deployment, Team, Repo, RepoProviderUser, Commit
from src import logger, dbi, db
from src.helpers.provider_user_helper import current_provider_user
from src.api_responses.errors import *
from src.api_responses.success import *
from src.utils import clusters, log_streamer, dataset_db
from src.helpers.definitions import core_header_name
from src.deploys.build_server_deploy import BuildServerDeploy
from src.utils.job_queue import job_queue
from src.utils.pyredis import redis
from src.utils.pred_messenger import PredMessenger
from src.helpers.deployment_statuses import ds
from src.utils.log_formatter import training_log
from src.helpers.provider_helper import parse_git_url
from sqlalchemy.orm import joinedload

train_deployment_model = api.model('Deployment', {
  'git_url': fields.String(required=True),
  'model_ext': fields.String(required=True)
})

deployment_trained_model = api.model('Deployment', {
  'deployment_uid': fields.String(required=True),
  'with_api_deploy': fields.Boolean(required=True)
})

api_deployment_model = api.model('Deployment', {
  'git_url': fields.String(required=True)
})


@namespace.route('/deployment/push')
class PushDeployment(Resource):
  """Make a full deployment (train + api deploys)"""

  @namespace.doc('push_deployment')
  @namespace.expect(train_deployment_model, validate=True)
  def post(self):
    return perform_train_deploy(with_api_deploy=True)


@namespace.route('/deployment/train')
class TrainDeployment(Resource):
  """Make a train deployment"""

  @namespace.doc('train_deployment')
  @namespace.expect(train_deployment_model, validate=True)
  def post(self):
    return perform_train_deploy()


@namespace.route('/deployment/trained')
class DeploymentTrained(Resource):
  """Train cluster reporting that a deployment is trained"""

  @namespace.doc('deployment_trained')
  @namespace.expect(deployment_trained_model, validate=True)
  def put(self):
    # Ensure request coming from our train cluster
    if request.headers.get(core_header_name) != os.environ.get('CORE_API_TOKEN'):
      return '', 401

    # Get required params
    deployment_uid = api.payload['deployment_uid']
    with_api_deploy = api.payload['with_api_deploy']
    update_prediction_model = api.payload['update_prediction_model']

    # Get deployment for uid
    deployment = dbi.find_one(Deployment, {'uid': deployment_uid})

    # Ensure deployment exists
    if not deployment:
      err = 'No Deployment found for uid: {}'.format(deployment_uid)
      logger.error(err)
      return err, 500

    # Ensure deployment status is TRAINING
    if deployment.status != ds.TRAINING:
      err = 'Invalid deployment status change: {} --> {}'.format(deployment.status, ds.DONE_TRAINING)
      logger.error(err)
      return err, 500

    # Update deployment to DONE_TRAINING status
    deployment = dbi.update(deployment, {'status': ds.DONE_TRAINING})

    # Update the Dataset's last_train_record_count
    # TODO -- this is sloppy and could be inaccurate if records were added in the time it took to train
    # Cache this value in redis somewhere and only update it at this point since the training succeeded.
    datasets = deployment.repo.datasets

    if datasets:
      dataset = datasets[0]
      record_count = dataset_db.record_count(table=dataset.table())
      dbi.update(dataset, {'last_train_record_count': record_count})
    else:
      logger.warn('Found no datasets for repo, Repo(id={}) -- not updating last_train_record_count.'.format(deployment.repo.id))

    # Get the deployment's train_job
    train_job = deployment.train_job

    if train_job:
      train_job.end()  # mark the train_job as ended
    else:
      logger.warn('Deployment(uid={}) has no train_job for some reason...'.format(deployment.uid))

    if with_api_deploy:  # continue on, deploying to API cluster
      deployer = BuildServerDeploy(deployment_uid=deployment.uid, build_for=clusters.API)
      job_queue.add(deployer.deploy, meta={'deployment': deployment.uid})
      dbi.update(deployment, {'status': deployment.statuses.API_BUILD_SCHEDULED})
    elif update_prediction_model:  # tell the API cluster to pull the latest model
      pred_messenger = PredMessenger(repo_uid=deployment.repo.uid)
      job_queue.add(pred_messenger.update_model)

    return '', 200


@namespace.route('/deployment/api')
class ApiDeployment(Resource):
  """Make a deployment to a team's API cluster"""

  @namespace.doc('api_deployment')
  @namespace.expect(api_deployment_model, validate=True)
  def post(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    # Get refs to payload info
    git_url = api.payload['git_url']

    provider_domain, team_name, repo_name = parse_git_url(git_url)

    # Find the provider by the passed domain
    provider = dbi.find_one(Provider, {'domain': provider_domain})

    if not provider:
      return PROVIDER_NOT_FOUND

    if provider != provider_user.provider:
      return PROVIDER_MISMATCH

    # Find repo for this team through provider
    team_slug = slugify(team_name, separator='-', to_lower=True)
    team = dbi.find_one(Team, {'slug': team_slug, 'provider': provider})

    if team:
      repo_slug = slugify(repo_name, separator='-', to_lower=True)
      repo = dbi.find_one(Repo, {'team': team, 'slug': repo_slug})
    else:
      repo = None

    if not repo:
      return REPO_NOT_REGISTERED

    repo_provider_user = dbi.find_one(RepoProviderUser, {
      'repo': repo,
      'provider_user': provider_user
    })

    if not repo_provider_user:
      return NOT_ASSOCIATED_WITH_REPO

    if repo_provider_user.role < RepoProviderUser.roles.MEMBER_WRITE:
      return INVALID_REPO_PERMISSIONS

    # Get all deployments for this repo, ordered by most recently created
    deployments = repo.ordered_deployments()

    # We can only make an API deploy on an existing deploy...
    if not deployments:
      return NO_DEPLOYMENT_TO_SERVE

    # Get latest deployment for repo
    latest_deployment = deployments[0]

    # Get the index of the latest deployment's status
    latest_deployment_status_idx = ds.statuses.index(latest_deployment.status)
    done_training_idx = ds.statuses.index(ds.DONE_TRAINING)

    # If the latest deployment isn't done training yet...
    if latest_deployment_status_idx < done_training_idx:
      # TODO: incorporate Deployment.failed here
      return LATEST_DEPLOYMENT_TRAINING

    # If latest deploy is already in the process of API deploying, say everything's up-to-date
    if latest_deployment_status_idx > done_training_idx and not latest_deployment.failed:
      return DEPLOYMENT_UP_TO_DATE

    logger.info('New deployment detected to serve: {}'.format(latest_deployment.commit.sha),
                queue=latest_deployment.uid,
                section=True)

    logger.info('Scheduling API build...', queue=latest_deployment.uid, section=True)

    deployer = BuildServerDeploy(deployment_uid=latest_deployment.uid, build_for=clusters.API)

    job_queue.add(deployer.deploy, meta={'deployment': latest_deployment.uid})

    # Note who triggered this api deploy
    dbi.update(latest_deployment, {
      'serve_triggered_by': provider_user.username,
      'status': latest_deployment.statuses.API_BUILD_SCHEDULED
    })

    return Response(stream_with_context(log_streamer.from_list(latest_deployment.uid)),
                    headers={'X-Accel-Buffering': 'no'})


@namespace.route('/deployment/logs')
class TrainDeployment(Resource):
  """Get training logs for a deployment"""

  @namespace.doc('get_training_logs')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    # Get refs to payload info
    args = dict(request.args.items())
    git_url = args.get('git_url')
    
    if not git_url:
      return INVALID_INPUT_PAYLOAD

    provider_domain, team_name, repo_name = parse_git_url(git_url)

    # Find the provider by the passed domain
    provider = dbi.find_one(Provider, {'domain': provider_domain})

    if not provider:
      return PROVIDER_NOT_FOUND

    if provider != provider_user.provider:
      return PROVIDER_MISMATCH

    # Find repo for this team through provider
    team_slug = slugify(team_name, separator='-', to_lower=True)
    team = dbi.find_one(Team, {'slug': team_slug, 'provider': provider})

    if team:
      repo_slug = slugify(repo_name, separator='-', to_lower=True)
      repo = dbi.find_one(Repo, {'team': team, 'slug': repo_slug})
    else:
      repo = None

    if not repo:
      return REPO_NOT_REGISTERED

    if args.get('uid'):
      deployment = dbi.find_one(Deployment, {'uid': args.get('uid')})

      if not deployment:
        return DEPLOYMENT_NOT_FOUND
    else:
      # Get all deployments for this repo, ordered by most recently created
      deployments = repo.ordered_deployments()

      if not deployments:
        return NO_DEPLOYMENT_TO_SERVE

      # Get latest deployment for repo
      deployment = deployments[0]

    log_stream_key = 'train-{}'.format(deployment.uid)  # redis key for the log stream
    follow_logs = args.get('follow') == 'true'  # Do they want to follow the real-time logs or no?

    if follow_logs:
      # Stream real-time training logs for the latest deploy
      return Response(stream_with_context(log_streamer.from_stream(log_stream_key)),
                      headers={'X-Accel-Buffering': 'no'})
    else:
      # Following real-time logs is NOT desired here. Just send back a dump of
      # all the current logs up to this point.

      # Get all logs from redis stream
      current_logs = redis.xrange(log_stream_key)

      if not current_logs:
        return NO_LOGS_TO_SHOW

      # Format a list of just the log text messages
      log_messages = [training_log(data).rstrip() for ts, data in current_logs]

      return {'logs': log_messages}


@namespace.route('/logtest')
class LogTest(Resource):
  def get(self):
    from time import sleep

    def func():
      i = 0

      while True:
        i += 1
        sleep(2)
        yield 'a'*1024 + 'Line {}\n'.format(i)

    return Response(stream_with_context(func()),
                    headers={'X-Accel-Buffering': 'no'})


@namespace.route('/deployments')
class GetDeployments(Resource):
  """Fetch deployments for a repo"""

  @namespace.doc('get_deployments_for_repo')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    args = dict(request.args.items())
    team_slug = args.get('team')
    repo_slug = args.get('repo')

    if not team_slug:
      logger.error('No team provided during request for project datasets')
      return INVALID_INPUT_PAYLOAD

    if not repo_slug:
      logger.error('No repo provided during request for project datasets')
      return INVALID_INPUT_PAYLOAD

    team_slug = team_slug.lower()
    team = dbi.find_one(Team, {'slug': team_slug})

    if not team:
      return TEAM_NOT_FOUND

    repo_slug = repo_slug.lower()

    repo = [r for r in provider_user.repos() if r.team_id == team.id and r.slug == repo_slug]

    if not repo:
      return REPO_NOT_FOUND

    repo = repo[0]

    resp = {'deployments': []}

    deployments = db.session.query(Deployment) \
      .options(joinedload(Deployment.commit)) \
      .filter_by(repo_id=repo.id) \
      .order_by(Deployment.created_at).all()

    if not deployments:
      return resp

    deployments.reverse()

    for d in deployments:
      commit = d.commit
      train_job = d.train_job

      if train_job:
        train_duration_sec = train_job.duration().seconds
      else:
        train_duration_sec = 0

      resp['deployments'].append({
        'uid': d.uid,
        'status': d.status,
        'failed': d.failed,
        'canceled': False,
        'created_at': utcnow_to_ts(d.created_at),
        'train_duration_sec': train_duration_sec,
        'commit': {
          'sha': commit.sha,
          'branch': commit.branch,
          'message': commit.message,
          'author': commit.author,
          'author_icon': commit.author_icon
        }
      })

    return resp


@namespace.route('/deployment')
class GetDeployment(Resource):
  """Fetch deployment"""

  @namespace.doc('get_deployment')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    args = dict(request.args.items())
    deployment_uid = args.get('uid')

    if not deployment_uid:
      return INVALID_INPUT_PAYLOAD

    # TODO: Validate that deployment is accessible by provider_user

    deployment = dbi.find_one(Deployment, {'uid': deployment_uid})

    if not deployment:
      return DEPLOYMENT_NOT_FOUND

    commit = deployment.commit

    ordered_deploy_statuses = deployment.statuses.statuses

    if ordered_deploy_statuses.index(deployment.status) > ordered_deploy_statuses.index(deployment.statuses.DONE_TRAINING):
      triggered_by = deployment.serve_triggered_by or deployment.train_triggered_by
    else:
      triggered_by = deployment.train_triggered_by

    resp = {
      'uid': deployment.uid,
      'status': deployment.status,
      'failed': deployment.failed,
      'canceled': False,
      'created_at': utcnow_to_ts(deployment.created_at),
      'triggered_by': triggered_by,
      'commit': {
        'sha': commit.sha,
        'branch': commit.branch,
        'message': commit.message,
        'author': commit.author,
        'author_icon': commit.author_icon
      }
    }

    return resp


def perform_train_deploy(with_api_deploy=False):
  provider_user = current_provider_user()

  if not provider_user:
    return UNAUTHORIZED

  # Get refs to payload info
  git_url = api.payload['git_url']
  model_ext = api.payload['model_ext']

  provider_domain, team_name, repo_name = parse_git_url(git_url)

  # Find the provider by the passed domain
  provider = dbi.find_one(Provider, {'domain': provider_domain})

  if not provider:
    return PROVIDER_NOT_FOUND

  if provider != provider_user.provider:
    return PROVIDER_MISMATCH

  # Find repo for this team through provider
  team_slug = slugify(team_name, separator='-', to_lower=True)
  team = dbi.find_one(Team, {'slug': team_slug, 'provider': provider})

  if team:
    repo_slug = slugify(repo_name, separator='-', to_lower=True)
    repo = dbi.find_one(Repo, {'team': team, 'slug': repo_slug})
  else:
    repo = None

  if not repo:
    return REPO_NOT_REGISTERED

  repo_provider_user = dbi.find_one(RepoProviderUser, {
    'repo': repo,
    'provider_user': provider_user
  })

  if not repo_provider_user:
    return NOT_ASSOCIATED_WITH_REPO

  if repo_provider_user.role < RepoProviderUser.roles.MEMBER_WRITE:
    return INVALID_REPO_PERMISSIONS

  # Always update the repo's model extension
  repo = dbi.update(repo, {'model_ext': model_ext})

  try:
    provider_client = provider.client()(provider_user.access_token)
    external_repo = provider_client.get_repo(repo.full_name(), lazy=False)
    commits = external_repo.get_commits()  # get first page of commits for repo
  except BaseException as e:
    logger.error('Error fetching commits for repo(uid={}): {}'.format(repo.uid, e))
    return ERROR_FETCHING_REPO

  try:
    latest_ext_commit = commits[0]  # get latest external commit
  except IndexError:
    return NO_COMMITS_IN_REPO
  except BaseException as e:
    logger.error('Error parsing commits for repo(uid={}): {}'.format(repo.uid, e))
    return ERROR_PARSING_COMMITS_FOR_REPO

  # Get all deployments for this repo, ordered by most recently created
  deployments = repo.ordered_deployments()

  # Tell user everything is up-to-date if latest deploy has same sha
  # as latest commit and hasn't failed.
  if deployments and deployments[0].commit.sha == latest_ext_commit.sha and not deployments[0].failed:
    return DEPLOYMENT_UP_TO_DATE

  # Upsert the commit
  commit = dbi.find_one(Commit, {'sha': latest_ext_commit.sha})

  if not commit:
    author = latest_ext_commit.author

    commit = dbi.create(Commit, {
      'sha': latest_ext_commit.sha,
      'message': latest_ext_commit.commit.message,
      'author': author.login,
      'author_icon': author.avatar_url
    })

  train_triggered_by = provider_user.username
  serve_triggered_by = None

  if with_api_deploy:
    serve_triggered_by = train_triggered_by

  # Create new deployment for repo
  deployment = dbi.create(Deployment, {
    'repo': repo,
    'commit': commit,
    'train_triggered_by': train_triggered_by,
    'serve_triggered_by': serve_triggered_by
  })

  logger.info('New SHA detected: {}'.format(commit.sha), queue=deployment.uid, section=True)

  logger.info('Scheduling training build...', queue=deployment.uid, section=True)

  deployer = BuildServerDeploy(deployment_uid=deployment.uid,
                               build_for=clusters.TRAIN,
                               full_push=with_api_deploy)

  job_queue.add(deployer.deploy, meta={'deployment': deployment.uid})

  # Update deployment status to TRAIN_BUILD_SCHEDULED
  deployment = dbi.update(deployment, {'status': deployment.statuses.TRAIN_BUILD_SCHEDULED})

  return Response(stream_with_context(log_streamer.from_list(deployment.uid)),
                  headers={'X-Accel-Buffering': 'no'})