from flask import request, redirect
from flask_restplus import Resource
from src.routes import namespace, api
from src.models import Integration, Prediction, PredictionIntegration
from src.api_responses.errors import *
from src.api_responses.success import *
from src import logger, dbi, db
from src.integrations.gh import GH


@namespace.route('/github/installed')
class Installed(Resource):
  """
  Hit any time a GitHub user installs the TensorCI GitHub App

  args:
    - installation_id (int)
  """
  def get(self):
    args = dict(request.args.items())
    installation_id = args.get('installation_id')

    if not installation_id:
      logger.error()
      return

    try:
      installation_id = int(installation_id)
    except:
      logger.error()
      return

    github = GH()

    try:
      # Use pem file and special payload to create a JWT
      # Use JWT as header ("Authorization: Bearer YOUR_JWT") to request installation access_token
      #   https://api.github.com/installations/:installation_id/access_tokens
      #   # => {'token': 'asdfasdf'}
      # Create new client for GH...Github(access_token=<token>)
      installation = github.get_installation(installation_id)
      repos = github.repo_urls_for_installation(installation)
    except BaseException as e:
      logger.error()
      return

    for repo in repos:
      try:
        prediction = dbi.find_one(Prediction, {'git_repo': repo})

        if not prediction:
          # Redirect somewhere for user to name prediction and create team if need be.
          # Will need to store the installation_id somewhere though in the meantime...maybe a draft table or something
          redirect('/finishthisshit')

        prediction_integration, is_new = dbi.upsert(PredictionIntegration, {
          'prediction': prediction,
          'integration': github.integration
        })

        dbi.update(prediction_integration, {'installation_id': installation_id})
      except BaseException as e:
        logger.error()
        return

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

