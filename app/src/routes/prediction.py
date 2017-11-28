from flask_restplus import Resource, fields
from src.routes import namespace, api
from src.models import TeamUser, Team, Prediction
from src import logger, dbi
from src.helpers.user_helper import current_user
from src.api_responses.errors import *
from src.api_responses.success import *
from slugify import slugify
from src.utils import clusters
from src.config import get_config
from src.statuses.pred_statuses import pstatus
from src.services.prediction_services import status_update_services
from src.deploys import create_deploy
from src.deploys.build_server_deploy import BuildServerDeploy

config = get_config()

create_prediction_model = api.model('Prediction', {
  'team_uid': fields.String(required=True),
  'name': fields.String(required=True),
  'git_repo': fields.String(required=True)
})

update_prediction_status_model = api.model('Prediction', {
  'status': fields.String(required=True),
  'prediction_uid': fields.String(required=True)
})


@namespace.route('/prediction')
class RestfulPrediction(Resource):
  """Restful Prediction Interface"""

  @namespace.doc('create_new_prediction_for_team')
  @namespace.expect(create_prediction_model, validate=True)
  def post(self):
    # Get current user
    user = current_user()

    if not user:
      return UNAUTHORIZED

    # Get requested team
    team = dbi.find_one(Team, {'uid': api.payload['team_uid']})

    if not team:
      return TEAM_NOT_FOUND

    # Make sure the current user is the owner of this Team (and therefore can create a Prediction)
    owner = dbi.find_one(TeamUser, {
      'team': team,
      'user': user,
      'role': TeamUser.roles.OWNER
    })

    # Only owners can create predictions
    if not owner:
      return FORBIDDEN

    prediction_name = api.payload['name']
    prediction_slug = slugify(prediction_name, separator='-', to_lower=True)

    # Ensure there's no Prediction with the same name for this Team
    if dbi.find_one(Prediction, {'team': team, 'slug': prediction_slug}):
      return PREDICTION_NAME_TAKEN

    git_repo = api.payload['git_repo']
    sha = api.payload.get('sha') or '8545012f4aa9bc3f3201fa643b5849e9e1dafc76'
    # Hardcode SHA for now

    try:
      # Create new prediction
      # prediction = dbi.create(Prediction, {
      #   'team': team,
      #   'name': prediction_name,
      #   'git_repo': git_repo,
      #   'sha': sha
      # })

      prediction = dbi.find_one(Prediction, {'uid': '1011f9fed0424c7cbd5ff2a91e4725b0'})

      # Schedule a deploy to the build server
      create_deploy(BuildServerDeploy, {
        'prediction_uid': prediction.uid,
        'build_for': clusters.TRAIN
      })
    except BaseException as e:
      logger.error('Error creating Prediction(name={}, team={}, git_repo={}): {}'.format(
        prediction_name, team, git_repo, e))
      return UNKNOWN_ERROR

    return PREDICTION_CREATION_SUCCESS


@namespace.route('/prediction/status')
class PredictionIsTrained(Resource):
  """Managing Prediction as a state machine"""

  @namespace.doc('update_prediction_status')
  @namespace.expect(update_prediction_status_model, validate=True)
  def put(self):
    # Get required params
    prediction_uid = api.payload['prediction_uid']
    desired_status = api.payload['status']

    # Find prediction for the requested uid
    prediction = dbi.find_one(Prediction, {'uid': prediction_uid})

    # Ensure prediction exists
    if not prediction:
      err = 'No Prediction found for uid: {}'.format(prediction_uid)
      logger.error(err)
      return err, 500

    # Ensure desired_status is even a valid status
    if desired_status not in pstatus.statuses:
      err = 'Invalid desired_status: {}'.format(desired_status)
      logger.error(err)
      return err, 500

    # Ensure desired_status immediately proceeds this prediction's current status
    if not pstatus.proceeds(prediction.status, desired_status):
      err = '{} does not immediately proceed: {}'.format(desired_status, prediction.status)
      logger.error(err)
      return err, 500

    # Get status update service for the desired_status
    update_service = status_update_services.get(desired_status)

    if not update_service:
      err = 'Couldn\'t find status update service for status: {}'.format(desired_status)
      logger.error(err)
      return err, 500

    # Perform the update
    service = update_service(prediction=prediction)
    service.perform()

    return '', 200