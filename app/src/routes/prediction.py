from flask_restplus import Resource, fields
from src.routes import namespace, api
from src.models import TeamUser, Team, Prediction
from src import logger, dbi
from src.helpers.user_helper import current_user
from src.api_responses.errors import *
from src.api_responses.success import *
from slugify import slugify
from src.utils import deployer, clusters, image_names
from src.config import get_config

config = get_config()

create_prediction_model = api.model('Prediction', {
  'team_uid': fields.String(required=True),
  'name': fields.String(required=True),
  'git_repo': fields.String(required=True)
})


@namespace.route('/prediction')
class RestfulPrediction(Resource):
  """Restful Prediction Interface"""

  @namespace.doc('create_new_prediction_for_team')
  @namespace.expect(create_prediction_model, validate=True)
  def post(self):
    user = current_user()

    if not user:
      return UNAUTHORIZED

    team = dbi.find_one(Team, {'uid': api.payload['team_uid']})

    if not team:
      return TEAM_NOT_FOUND

    # Make sure this User is the owner of this Team (and therefore can create a Prediction)
    owner = dbi.find_one(TeamUser, {
      'team': team,
      'user': user,
      'role': TeamUser.roles.OWNER
    })

    if not owner:
      return FORBIDDEN

    prediction_name = api.payload['name']
    prediction_slug = slugify(prediction_name, separator='-', to_lower=True)

    # Ensure there's no Prediction with the same name for this Team
    if dbi.find_one(Prediction, {'team': team, 'slug': prediction_slug}):
      return PREDICTION_NAME_TAKEN

    try:
      # Create new prediction
      prediction = dbi.create(Prediction, {
        'team': team,
        'name': prediction_name,
        'git_repo': api.payload['git_repo']
      })

      image = '{}/{}'.format(config.IMAGE_REPO_OWNER, image_names.BUILD_SERVER)

      # Deploy to Build Server
      deployer.deploy(prediction.name,
                      image=image,
                      to_cluster=clusters.BUILD_SERVER,
                      for_cluster=clusters.TRAIN)

    except BaseException as e:
      logger.error('Error creating Prediction(name={}, team={}, git_repo={}): {}'.format(
        prediction_name, team, api.payload['git_repo'], e))
      return UNKNOWN_ERROR

    return PREDICTION_CREATION_SUCCESS


@namespace.route('/prediction/trained')
class PredictionIsTrained(Resource):

  @namespace.doc('trained_model_is_api_ready')
  def post(self):
    # Validate the request (via external token? where's this request coming from?)

    # Get prediction from token

    # Get team through prediction

    # If team doesn't have API Cluster yet...

      # Create Cluster model name=<team_slug>-cluster.domain.ai

      # Create S3 Bucket for this cluster (name=cluster.name)

      # Create Route 53 hosted zone (name=cluster.name), returning the list of nameserver addresses associated with that zone

      # Register NS records for each of the nameserver addresses returned by last command
      #   domain: cluster.name
      #   record: <address>

      # Create cluster with kops name=cluster.name

      # Validate the cluster...(this will take minutes, so schedule what follows as callback jobs)

      # Take the prediction's github repo, give it the api docker file, build an image from that, upload that image,
      # and then deploy the api image to the newly created cluster

      # The API image will pull the trained model from S3 upon startup

    # Else...

      # Hit the team's API Cluster

    return '', 200
