from flask import request
from flask_restplus import Resource
from src.routes import namespace, api
from src.models import Integration
from src import logger, dbi


@namespace.route('/oauth/<string:slug>')
class OAuth(Resource):

  @namespace.doc('oauth_callback')
  def post(self, slug):
    print slug
    return ''