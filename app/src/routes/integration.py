from flask import request
from flask_restplus import Resource
from src.routes import namespace, api
from src.models import Integration
from src import logger, dbi


@namespace.route('/oauth/<string:slug>')
class OAuth(Resource):
  """
  OAuth callback endpoint for integrations
  """
  @namespace.doc('oauth_callback')
  def post(self, slug):
    return ''


@namespace.route('/webhook/<string:slug>')
class Webhook(Resource):
  """
  Webhook endpoint for integrations
  """
  @namespace.doc('integrations_webhook')
  def post(self, slug):
    return ''