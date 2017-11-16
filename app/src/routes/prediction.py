from flask_restplus import Resource
from src.routes import namespace, api


@namespace.route('/prediction')
class RestfulPrediction(Resource):
  """Restful Prediction Interface"""

  @namespace.doc('create_new_prediction_for_team')
  def post(self):
    # Assume input here is github repo

    # Get user from token

    # Validate user exists

    # Get team from user

    # INSERT new Prediction to DB

    # Take the github repo, give it the training docker file, build an image from that, upload that image,
    # and then deploy the training image to your training cluster

    return '', 201


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

      # Hit the team's API Cluster's API telling it to fetch the latest trained model from S3

    return '', 200
