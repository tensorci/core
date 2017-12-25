from flask import request
from flask_restplus import Resource
from src.routes import namespace, api
from src.models import Integration, Prediction, PredictionIntegration
from src.api_responses.errors import *
from src.api_responses.success import *
from src import logger, dbi
from src.services.integration_services.oauth_token_exchange import OAuthTokenExchange
from src.config import get_config

config = get_config()


@namespace.route('/oauth/<string:slug>')
class OAuth(Resource):
  """
  OAuth callback endpoint for integrations
  """
  @namespace.doc('oauth_callback')
  def get(self, slug):
    # TODO: evaluate fact that you're publicly exposing an N+1 query for this public endpoint
    integration = dbi.find_one(Integration, {'slug': slug})

    if not integration:
      return INTEGRATION_NOT_FOUND

    args = dict(request.args.items())
    temp_code = args.get('code')
    state = args.get('state')

    if not temp_code:
      logger.error('No temporary "code" arg provided in OAuth redirect for integration, {}'.format(slug))
      return INVALID_OAUTH_TEMP_CODE

    if not state:
      logger.error('No "state" arg provided in OAuth redirect for integration, {}'.format(slug))
      return INVALID_OAUTH_STATE_VALUE

    prediction = dbi.find_one(Prediction, {'uid': state})

    if not prediction:
      return PREDICTION_NOT_FOUND

    try:
      token_swap_svc = OAuthTokenExchange(integration=integration,
                                          temp_code=temp_code,
                                          redirect_uri='http://localhost:5000/api/oauth/github',
                                          state=state)
      token_swap_svc.perform()
    except BaseException as e:
      logger.error('Error executing oauth_token_exchange for prediction(uid={}), integration(slug={}): {}'.format(
        state, slug, e))
      return OAUTH_TOKEN_SWAP_FAILED

    if not token_swap_svc.access_token:
      logger.error('Access token still empty after requesting (prediction(uid={}), integration(slug={}))'.format(
        state, slug))
      return OAUTH_TOKEN_SWAP_FAILED

    try:
      pred_integration, is_new = dbi.upsert(PredictionIntegration, {
        'prediction': prediction,
        'integration': integration
      })
    except BaseException as e:
      logger.error('Error upserting PredictionIntegration (prediction(uid={}), integration(slug={}): {}'.format(
        state, slug, e))
      return PREDICTION_INTEGRATION_UPSERT_FAILED

    if pred_integration.api_key != token_swap_svc.access_token:
      dbi.update(pred_integration, {'api_key': token_swap_svc.access_token})

    # TODO: I think this is a user token, so we'll probably save this in a new UserIntegration model

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

    logger.info('{} webhook heard'.format(slug))
    logger.info('Payload: {}'.format(api.payload))
    logger.info('Headers: {}'.format(request.headers))

    return {}, 200