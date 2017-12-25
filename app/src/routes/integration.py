from flask import request
from flask_restplus import Resource
from src.routes import namespace, api
from src.models import Integration, Prediction, PredictionIntegration
from src.api_responses.errors import *
from src.api_responses.success import *
from src import logger, dbi


@namespace.route('/installed/<string:slug>')
class Installed(Resource):
  def get(self, slug):
    integration = dbi.find_one(Integration, {'slug': slug})

    if not integration:
      return INTEGRATION_NOT_FOUND

    args = dict(request.args.items())
    installation_id = args.get('installation_id')

    return {}, 200


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
    logger.info('Args: {}'.format(request.args.items()))
    logger.info('Headers: {}'.format(request.headers))

    return {}, 200

