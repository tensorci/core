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
from src.utils.log_formatter import training_log
from src.helpers.provider_helper import parse_git_url
from src.helpers.deployment_helper import current_stage, format_stages
from sqlalchemy.orm import joinedload
from datetime import datetime

train_deployment_model = api.model('Deployment', {
  'git_url': fields.String(required=True)
})

deployment_trained_model = api.model('Deployment', {
  'deployment_uid': fields.String(required=True),
  'update_prediction_model': fields.Boolean(required=True)
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
    return perform_train_deploy(intent=Deployment.intents.SERVE)


@namespace.route('/deployment/train')
class TrainDeployment(Resource):
  """Make a train deployment"""

  @namespace.doc('train_deployment')
  @namespace.expect(train_deployment_model, validate=True)
  def post(self):
    return perform_train_deploy(intent=Deployment.intents.TRAIN)


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
    update_prediction_model = api.payload['update_prediction_model']
    model_ext = api.payload.get('model_ext', '')

    # Get deployment for uid
    deployment = dbi.find_one(Deployment, {'uid': deployment_uid})

    # Ensure deployment exists
    if not deployment:
      err = 'No Deployment found for uid: {}'.format(deployment_uid)
      logger.error(err)
      return err, 500

    # Ensure deployment status is TRAINING
    if deployment.status != deployment.statuses.TRAINING:
      err = 'Invalid deployment status change: {} --> {}'.format(deployment.status, deployment.statuses.DONE_TRAINING)
      logger.error(err)
      return err, 500

    # Update deployment to DONE_TRAINING status
    deployment = dbi.update(deployment, {'status': deployment.statuses.DONE_TRAINING})

    # Update repo's model_ext column
    dbi.update(deployment.repo, {'model_ext': model_ext})

    # Enqueue this message in order to force the deployment_update_queue to broadcast an update.
    logger.info('Done training.',
                stream='done-training:{}'.format(deployment.uid),
                stage=deployment.statuses.DONE_TRAINING)

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

    # If deployment is meant for the API cluster, continue on...
    if deployment.intent_to_serve():
      log_stream_key = deployment.api_deploy_log()
      stage = deployment.statuses.BUILDING_FOR_API

      logger.info('New deployment detected to serve: {}'.format(deployment.commit.sha),
                  stream=log_stream_key,
                  section=True,
                  stage=stage)

      logger.info('Scheduling API build...', stream=log_stream_key, section=True, stage=stage)

      deployer = BuildServerDeploy(deployment_uid=deployment.uid, build_for=clusters.API)
      job_queue.add(deployer.deploy, meta={'deployment': deployment.uid})
      dbi.update(deployment, {'status': deployment.statuses.API_BUILD_SCHEDULED})

    # If the API cluster just needs to pull the latest trained model, tell it to do so.
    elif update_prediction_model:
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

    if not deployments:
      return NO_DEPLOYMENT_TO_SERVE

    # Find the latest deployment that's either:
    # (a) A failed api deployment
    # (b) A succeeded train deployment
    # which ever one comes first
    deployment = None
    for dep in deployments:
      if (dep.intent_to_serve() and dep.failed) or \
        (dep.intent_to_train() and not dep.failed and dep.status == dep.statuses.DONE_TRAINING):
        deployment = dep
        break

    # If no api-deployable deployment was found, everything is up-to-date.
    if not deployment:
      return DEPLOYMENT_UP_TO_DATE

    log_stream_key = deployment.api_deploy_log()
    stage = deployment.statuses.BUILDING_FOR_API

    logger.info('New deployment detected to serve: {}'.format(deployment.commit.sha),
                stream=log_stream_key,
                section=True,
                stage=stage)

    logger.info('Scheduling API build...', stream=log_stream_key, section=True, stage=stage)

    deployer = BuildServerDeploy(deployment_uid=deployment.uid, build_for=clusters.API)

    job_queue.add(deployer.deploy, meta={'deployment': deployment.uid})

    dbi.update(deployment, {
      'serve_triggered_by': provider_user.username,
      'status': deployment.statuses.API_BUILD_SCHEDULED,
      'failed': False,  # Unfail the deployment in case we're retrying a failed API deploy
      'intent': deployment.intents.SERVE,  # Update the intent
      'intent_updated_at': datetime.utcnow()
    })

    # Respond with a stream of the deploy logs
    return Response(stream_with_context(log_streamer.stream_deploy_logs(deployment, stream_key=log_stream_key)),
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

    follow_logs = args.get('follow') == 'true'  # Do they want to follow the real-time logs or no?

    if follow_logs:
      # Stream real-time training logs for the latest deploy
      return Response(stream_with_context(log_streamer.stream_train_logs(deployment)),
                      headers={'X-Accel-Buffering': 'no'})
    else:
      # Following real-time logs is NOT desired here. Just send back a dump of
      # all the current logs up to this point.

      # Get all logs from redis stream
      current_logs = redis.xrange(deployment.train_log())

      if not current_logs:
        return NO_LOGS_TO_SHOW

      # Format a list of just the log text messages
      log_messages = [training_log(data, with_color=True).rstrip() for ts, data in current_logs]

      return {'logs': log_messages}


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
      logger.error('No team provided during request for deployments')
      return INVALID_INPUT_PAYLOAD

    if not repo_slug:
      logger.error('No repo provided during request for deployments')
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
      .order_by(Deployment.intent_updated_at).all()

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
        'readable_status': d.readable_status(),
        'failed': d.failed,
        'succeeded': d.succeeded(),
        'date': utcnow_to_ts(d.intent_updated_at),
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

    if deployment.status_greater_than(deployment.statuses.DONE_TRAINING):
      triggered_by = deployment.serve_triggered_by or deployment.train_triggered_by
    else:
      triggered_by = deployment.train_triggered_by

    resp = {
      'uid': deployment.uid,
      'readable_status': deployment.readable_status(),
      'intent': deployment.intent,
      'failed': deployment.failed,
      'succeeded': deployment.succeeded(),
      'date': utcnow_to_ts(deployment.intent_updated_at),
      'triggered_by': triggered_by,
      'commit': {
        'sha': commit.sha,
        'branch': commit.branch,
        'message': commit.message,
        'author': commit.author,
        'author_icon': commit.author_icon
      },
      'current_stage': current_stage(deployment),
      'stages': format_stages(deployment)
    }

    return resp


def perform_train_deploy(intent=None):
  provider_user = current_provider_user()

  if not provider_user:
    return UNAUTHORIZED

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

  try:
    # Fetch the first page of commits for this repo from the provider's API
    provider_client = provider.client()(provider_user.access_token)
    external_repo = provider_client.get_repo(repo.full_name(), lazy=False)
    commits = external_repo.get_commits()
  except BaseException as e:
    logger.error('Error fetching commits for repo(uid={}): {}'.format(repo.uid, e))
    return ERROR_FETCHING_REPO

  try:
    # Get the most recent external commit
    latest_ext_commit = commits[0]
  except IndexError:
    return NO_COMMITS_IN_REPO
  except BaseException as e:
    logger.error('Error parsing commits for repo(uid={}): {}'.format(repo.uid, e))
    return ERROR_PARSING_COMMITS_FOR_REPO

  # Get all deployments for this repo, ordered by most recently created.
  deployments = repo.ordered_deployments()
  latest_deployment = None

  # Get latest deployment if it exists.
  if deployments:
    latest_deployment = deployments[0]

  # Everything is already up-to-date if:
  # (1) A deployment for this commit already exists
  # (2) That deployment is on or has already passed the TRAIN_BUILD_SCHEDULED status.
  # (3) That deployment hasn't failed.
  if latest_deployment and latest_deployment.commit.sha == latest_ext_commit.sha \
    and latest_deployment.status_greater_than(latest_deployment.statuses.CREATED) \
    and not latest_deployment.failed:
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

  # If a full-push (Train + Serve) is desired, both train and serve are triggered by the same person.
  if intent == Deployment.intents.SERVE:
    serve_triggered_by = train_triggered_by

  # Create new deployment for repo & commit
  deployment = dbi.create(Deployment, {
    'repo': repo,
    'commit': commit,
    'train_triggered_by': train_triggered_by,
    'serve_triggered_by': serve_triggered_by,
    'intent': intent
  })

  log_stream_key = deployment.train_deploy_log()
  stage = deployment.statuses.BUILDING_FOR_TRAIN

  logger.info('New SHA detected: {}'.format(commit.sha), stream=log_stream_key, section=True, stage=stage)

  logger.info('Scheduling training build...', stream=log_stream_key, section=True, stage=stage)

  # Schedule a train build
  deployer = BuildServerDeploy(deployment_uid=deployment.uid, build_for=clusters.TRAIN)
  job_queue.add(deployer.deploy, meta={'deployment': deployment.uid})

  # Update deployment status to TRAIN_BUILD_SCHEDULED
  deployment = dbi.update(deployment, {'status': deployment.statuses.TRAIN_BUILD_SCHEDULED})

  if api.payload.get('with_log_stream') is False:
    return DEPLOYMENT_CREATION_SUCCESS

  # Respond with a stream of the deploy logs
  return Response(stream_with_context(log_streamer.stream_deploy_logs(deployment, stream_key=log_stream_key)),
                  headers={'X-Accel-Buffering': 'no'})