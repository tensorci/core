import os
import json
from flask_restplus import Resource, fields
from flask import request, Response, stream_with_context
from src.routes import namespace, api
from src.models import Prediction, Deployment
from src import logger, dbi
from src.helpers.user_helper import current_user
from src.api_responses.errors import *
from src.api_responses.success import *
from src.utils import clusters
from src.utils.gh import fetch_git_repo
from src.helpers.definitions import core_header_name
from src.deploys.build_server_deploy import BuildServerDeploy
from src.services.deployment_services import deployment_status_update_svcs
from src.utils.deployment_logger import DeploymentLogger
from src.utils.pyredis import redis
from src.utils.queue import job_queue
from time import sleep

create_deployment_model = api.model('Deployment', {
  'team_slug': fields.String(required=True),
  'prediction_slug': fields.String(required=True),
  'git_repo': fields.String(required=True)
})

update_deployment_status_model = api.model('Deployment', {
  'status': fields.String(required=True),
  'deployment_uid': fields.String(required=True)
})


@namespace.route('/deployment')
class RestfulDeployment(Resource):
  """Restful Deployment Interface"""

  # TODO: break the shit out of this function
  @namespace.doc('create_deployment')
  @namespace.expect(create_deployment_model, validate=True)
  def post(self):
    # Get current user
    user = current_user()

    if not user:
      return UNAUTHORIZED

    # Get refs to payload info
    team_slug = api.payload['team_slug']
    prediction_slug = api.payload['prediction_slug']
    git_repo = api.payload['git_repo']

    # Find a team for the provided team_slug that belongs to this user
    team = [t for t in user.teams() if t.slug == team_slug]

    if not team:
      return TEAM_NOT_FOUND

    team = team[0]

    # Find prediction for provided slug
    prediction = dbi.find_one(Prediction, {'slug': prediction_slug})

    # If prediction already belongs to another team, respond saying the name is not available
    if prediction and prediction.team != team:
      return PREDICTION_NAME_TAKEN

    is_new_prediction = not bool(prediction)
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

    # Update the prediction's repo regardless of if it's a new prediction
    prediction = dbi.update(prediction, {'git_repo': git_repo})

    # try:
    #   repo = fetch_git_repo(git_repo)  # fetch git repo
    #   commits = repo.get_commits()  # get first page of commits for repo
    # except BaseException as e:
    #   logger.error('Error fetching commits for repo: {} for prediction(slug={}): {}'.format(git_repo, prediction_slug, e))
    #   return ERROR_FETCHING_REPO
    #
    # try:
    #   latest_sha = commits[0].sha  # get sha of latest commit
    # except IndexError:
    #   return NO_COMMITS_IN_REPO
    # except BaseException as e:
    #   logger.error('Error parsing commits for repo: {} for prediction(slug={}): {}'.format(git_repo, prediction_slug, e))
    #   return ERROR_PARSING_COMMITS_FOR_REPO
    #
    # # Get all deployments for this prediction, ordered by most recently created
    # deployments = prediction.ordered_deployments()
    #
    # # Tell user everything is up-to-date if latest deploy has same sha
    # # as latest commit and hasn't failed.
    # if deployments and deployments[0].sha == latest_sha and not deployments[0].failed:
    #   return {'ok': True, 'up_to_date': True}
    #
    # # Create new deployment for prediction
    # deployment = dbi.create(Deployment, {
    #   'prediction': prediction,
    #   'sha': latest_sha
    # })
    #
    # # Create a deployment logger instance
    # dlogger = DeploymentLogger(deployment)
    #
    # # Log the above activity to the user
    # if is_new_prediction:
    #   dlogger.info('Created new prediction: {}'.format(prediction.slug))
    #
    # if updated_git_repo:
    #   dlogger.info('Updated prediction\'s git repo to {}'.format(git_repo))
    #
    # dlogger.info('New SHA detected: {}'.format(latest_sha))
    #
    # deployer = BuildServerDeploy(deployment_uid=deployment.uid, build_for=clusters.TRAIN)
    #
    # job_queue.enqueue(deployer.deploy, timeout=1800)

    @stream_with_context
    def stream_logs():
      while True:
        sleep(0.5)
        yield 'hey\n'
      # complete = False
      #
      # while not complete:
      #   item = redis.blpop(deployment.uid)
      #
      #   if not item:
      #     continue
      #
      #   try:
      #     item = json.loads(item[1])
      #   except BaseException:
      #     continue
      #
      #   complete = item.get('complete') == True
      #
      #   yield item.get('text') + '\n'

    return Response(stream_logs(), headers={'X-Accel-Buffering': 'no'})

  @namespace.doc('update_deployment_status')
  @namespace.expect(update_deployment_status_model, validate=True)
  def put(self):
    # Ensure request coming from an authed location
    if request.headers.get(core_header_name) != os.environ.get('CORE_API_TOKEN'):
      return '', 401

    # Get required params
    deployment_uid = api.payload['deployment_uid']
    desired_status = api.payload['status']

    # Get deployment for uid
    deployment = dbi.find_one(Deployment, {'uid': deployment_uid})

    # Ensure deployment exists
    if not deployment:
      err = 'No Deployment found for uid: {}'.format(deployment_uid)
      logger.error(err)
      return err, 500

    # Ensure desired_status to update to is a valid status
    if desired_status not in deployment.statuses.ordered_statuses:
      err = 'Invalid desired_status: {}'.format(desired_status)
      logger.error(err)
      return err, 500

    # Ensure desired_status directly proceeds this deployment's current status
    if not deployment.status_directly_proceeds(desired_status):
      err = '{} does not directly proceed: {}'.format(desired_status, deployment.status)
      logger.error(err)
      return err, 500

    # Get status update service for the desired_status
    update_service = deployment_status_update_svcs.get(desired_status)

    if not update_service:
      err = 'Couldn\'t find deployment status update service for status: {}'.format(desired_status)
      logger.error(err)
      return err, 500

    # Perform the update
    service = update_service(deployment=deployment)
    service.perform()

    return '', 200