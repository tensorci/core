import os
from flask_restplus import Resource, fields
from flask import request
from src.routes import namespace, api
from src.models import Prediction, Deployment
from src import logger, dbi
from src.helpers.user_helper import current_user
from src.api_responses.errors import *
from src.api_responses.success import *
from src.utils import clusters
from src.utils.gh import fetch_git_repo
from src.deploys import create_deploy
from src.helpers.definitions import core_header_name
from src.deploys.build_server_deploy import BuildServerDeploy
from src.services.deployment_services import deployment_status_update_svcs

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

    # Create new prediction for team if it didn't exist
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

    # Fetch remote repository object via the GitHub API
    repo = fetch_git_repo(git_repo)

    # Get the first page of commits for the repo
    commits = repo.get_commits()

    # Make sure the repo's not empty
    if len(commits) == 0:
      return EMPTY_REPO

    # Get the sha of the latest commit
    latest_sha = commits[0].sha

    # Get all deployments for this prediction, ordered by most recently created
    deployments = prediction.ordered_deployments()

    # Tell user everything is up-to-date if latest deploy has same sha as latest commit
    if deployments and deployments[0].sha == latest_sha:
      return {'ok': True, 'up_to_date': True}

    # Create new deployment for prediction
    deployment = dbi.create(Deployment, {
      'prediction': prediction,
      'sha': latest_sha
    })

    # Schedule a deploy to the build server
    create_deploy(BuildServerDeploy, {
      'deployment_uid': deployment.uid,
      'build_for': clusters.TRAIN
    })

    return DEPLOYMENT_CREATION_SUCCESS

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