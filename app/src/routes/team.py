from flask_restplus import Resource
from src.routes import namespace, api


@namespace.route('/team')
class RestfulTeam(Resource):
  """Restful Team Interface"""

  @namespace.doc('create_new_team')
  def post(self):
    # Get user from token

    # Validate user exists

    # Make sure team doesn't already exist for that slug

    # INSERT Team record to DB

    return '', 201