import os
from flask_restplus import Resource
from src.routes import namespace, api


@namespace.route('/team')
class RestfulTeam(Resource):
  """Restful Team Interface"""

  @namespace.doc('example_get_request')
  def get(self):
    return 'Secret: {}'.format(os.environ.get('SECRET')), 200