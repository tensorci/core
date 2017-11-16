import os
from flask_restplus import Resource
from src.routes import namespace, api


@namespace.route('/company')
class CreateUser(Resource):
  """Company Test Endpoint"""

  def get(self):
    return 'Secret: {}'.format(os.environ.get('SECRET')), 200