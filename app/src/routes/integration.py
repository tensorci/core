from flask_restplus import Resource
from src.routes import namespace, api
from src.models import Integration
from src.api_responses.errors import *
from src.api_responses.success import *
from src import logger, dbi


@namespace.route('/oauth/<string:slug>')
class OAuth(Resource):
  """
  OAuth callback endpoint for integrations
  """
  @namespace.doc('oauth_callback')
  def post(self, slug):
    integration = dbi.find_one(Integration, {'slug': slug})

    if not integration:
      return INTEGRATION_NOT_FOUND

    # Auth this request somehow?
    # Get temp code from payload
    # Get prediction-identifying info from payload
    # Request api token from temp code
    # Create new PredictionIntegration with api_token=<requested-api-token>, prediction, and integration

    return PREDICTION_INTEGRATION_CREATION_SUCCESS


@namespace.route('/webhook/<string:slug>')
class Webhook(Resource):
  """
  Webhook endpoint for integrations
  """
  @namespace.doc('integrations_webhook')
  def post(self, slug):
    integration = dbi.find_one(Integration, {'slug': slug})

    if not integration:
      return INTEGRATION_NOT_FOUND

    return ''