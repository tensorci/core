import os
from flask_restplus import Resource, fields
from flask import request, Response, stream_with_context
from src.routes import namespace, api
from src.models import Prediction, Deployment
from src import logger, dbi
from src.helpers.user_helper import current_user
from src.api_responses.errors import *
from src.api_responses.success import *
from src.utils import clusters, log_streamer
from src.utils.gh import fetch_git_repo
from src.helpers.definitions import core_header_name
from src.deploys.build_server_deploy import BuildServerDeploy
from src.utils.job_queue import job_queue
from src.utils.pyredis import redis
from src.utils.pred_messenger import PredMessenger
from src.helpers.deployment_statuses import ds
from src.utils.log_formatter import training_log

train_deployment_model = api.model('Deployment', {
  'team_slug': fields.String(required=True),
  'prediction_slug': fields.String(required=True),
  'git_repo': fields.String(required=True),
  'model_ext': fields.String(required=True)
})

deployment_trained_model = api.model('Deployment', {
  'deployment_uid': fields.String(required=True),
  'with_api_deploy': fields.Boolean(required=True)
})

api_deployment_model = api.model('Deployment', {
  'team_slug': fields.String(required=True),
  'prediction_slug': fields.String(required=True)
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

    if with_api_deploy:  # continue on, deploying to API cluster
      deployer = BuildServerDeploy(deployment_uid=deployment.uid, build_for=clusters.API)
      job_queue.add(deployer.deploy, meta={'deployment': deployment.uid})
    elif update_prediction_model:  # tell the API cluster to pull the latest model
      pred_messenger = PredMessenger(prediction_uid=deployment.prediction.uid)
      job_queue.add(pred_messenger.update_model)

    return '', 200


@namespace.route('/deployment/api')
class ApiDeployment(Resource):
  """Make a deployment to a team's API cluster"""

  @namespace.doc('api_deployment')
  @namespace.expect(api_deployment_model, validate=True)
  def post(self):
    # Get current user
    user = current_user()

    if not user:
      return UNAUTHORIZED

    # Get refs to payload info
    team_slug = api.payload['team_slug']
    prediction_slug = api.payload['prediction_slug']

    # Find a team for the provided team_slug that belongs to this user
    team = user.team_for_slug(team_slug)

    if not team:
      return TEAM_NOT_FOUND

    # Find prediction for provided slug and team
    prediction = dbi.find_one(Prediction, {'slug': prediction_slug, 'team': team})

    # Prediction required to already exist for API deploy
    if not prediction:
      return PREDICTION_NOT_FOUND

    # Get all deployments for this prediction, ordered by most recently created
    deployments = prediction.ordered_deployments()

    # We can only make an API deploy on an existing deploy...
    if not deployments:
      return NO_DEPLOYMENT_TO_SERVE

    # Get latest deployment for prediction
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

    logger.info('New deployment detected to serve: {}'.format(latest_deployment.sha),
                queue=latest_deployment.uid,
                section=True)

    logger.info('Scheduling API build...', queue=latest_deployment.uid, section=True)

    deployer = BuildServerDeploy(deployment_uid=latest_deployment.uid, build_for=clusters.API)
    job_queue.add(deployer.deploy, meta={'deployment': latest_deployment.uid})

    return Response(stream_with_context(log_streamer.from_list(latest_deployment.uid)),
                    headers={'X-Accel-Buffering': 'no'})


@namespace.route('/deployment/logs')
class TrainDeployment(Resource):
  """Get training logs for a deployment"""

  @namespace.doc('get_training_logs')
  def get(self):
    # Get current user
    user = current_user()

    if not user:
      return UNAUTHORIZED

    # Parse input args
    args = dict(request.args.items())
    team_slug = args.get('team_slug')
    prediction_slug = args.get('prediction_slug')

    if not team_slug or not prediction_slug:
      return INVALID_INPUT_PAYLOAD

    # Find a team for the provided team_slug that belongs to this user
    team = user.team_for_slug(team_slug)

    if not team:
      return TEAM_NOT_FOUND

    # Find prediction for provided slug and team
    prediction = dbi.find_one(Prediction, {'slug': prediction_slug, 'team': team})

    if not prediction:
      return PREDICTION_NOT_FOUND

    # Get all deployments for this prediction, ordered by most recently created
    deployments = prediction.ordered_deployments()

    if not deployments:
      return NO_DEPLOYMENT_TO_SERVE

    # Get latest deployment for prediction
    latest_deployment = deployments[0]

    log_stream_key = 'train-{}'.format(latest_deployment.uid)  # redis key for the log stream
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


def perform_train_deploy(with_api_deploy=False):
  # Get current user
  user = current_user()

  if not user:
    return UNAUTHORIZED

  # Get refs to payload info
  team_slug = api.payload['team_slug']
  prediction_slug = api.payload['prediction_slug']
  git_repo = api.payload['git_repo']
  model_ext = api.payload['model_ext']

  # Find a team for the provided team_slug that belongs to this user
  team = user.team_for_slug(team_slug)

  if not team:
    return TEAM_NOT_FOUND

  # Find prediction for provided slug
  prediction = dbi.find_one(Prediction, {'slug': prediction_slug})

  # If prediction already belongs to another team, respond saying the name is not available
  if prediction and prediction.team != team:
    return PREDICTION_NAME_TAKEN

  # Flags we care about for logging purposes
  is_new_prediction = not prediction
  updated_git_repo = not is_new_prediction and prediction.git_repo != git_repo

  if not prediction:
    try:
      prediction = dbi.create(Prediction, {
        'team': team,
        'name': prediction_slug
      })
    except BaseException as e:
      logger.error('Error creating Prediction(name={}, team={}): {}'.format(prediction_slug, team, e))
      return PREDICTION_CREATION_FAILED

  # Always update the prediction's repo and model extension
  prediction = dbi.update(prediction, {'git_repo': git_repo, 'model_ext': model_ext})

  try:
    repo = fetch_git_repo(git_repo)  # fetch git repo
    commits = repo.get_commits()  # get first page of commits for repo
  except BaseException as e:
    logger.error('Error fetching commits for repo: {} for prediction(slug={}): {}'.format(git_repo, prediction_slug, e))
    return ERROR_FETCHING_REPO

  try:
    latest_sha = commits[0].sha  # get sha of latest commit
  except IndexError:
    return NO_COMMITS_IN_REPO
  except BaseException as e:
    logger.error('Error parsing commits for repo: {} for prediction(slug={}): {}'.format(git_repo, prediction_slug, e))
    return ERROR_PARSING_COMMITS_FOR_REPO

  # Get all deployments for this prediction, ordered by most recently created
  deployments = prediction.ordered_deployments()

  # Tell user everything is up-to-date if latest deploy has same sha
  # as latest commit and hasn't failed.
  if deployments and deployments[0].sha == latest_sha and not deployments[0].failed:
    return DEPLOYMENT_UP_TO_DATE

  # Create new deployment for prediction
  deployment = dbi.create(Deployment, {
    'prediction': prediction,
    'sha': latest_sha
  })

  # Start showing logs to the user
  if is_new_prediction:
    logger.info('Creating new project'.format(prediction.slug), queue=deployment.uid, section=True)
    logger.info('Name: {}'.format(prediction.slug), queue=deployment.uid)

  if updated_git_repo:
    logger.info('Detected new git repository'.format(git_repo), queue=deployment.uid, section=True)
    logger.info('Repo: '.format(git_repo), queue=deployment.uid)

  logger.info('New SHA detected: {}'.format(latest_sha), queue=deployment.uid, section=True)

  logger.info('Scheduling training build...', queue=deployment.uid, section=True)

  deployer = BuildServerDeploy(deployment_uid=deployment.uid,
                               build_for=clusters.TRAIN,
                               full_push=with_api_deploy)

  job_queue.add(deployer.deploy, meta={'deployment': deployment.uid})

  return Response(stream_with_context(log_streamer.from_list(deployment.uid)),
                  headers={'X-Accel-Buffering': 'no'})