from flask_restplus import Resource, fields
from src.routes import namespace, api
from src.helpers.user_helper import current_user
from src.errors.responses import *
from psycopg2 import IntegrityError
from src.models import Team
from src import logger, dbi

create_team_model = api.model('Team', {
  'name': fields.String(required=True)
})


@namespace.route('/team')
class RestfulTeam(Resource):
  """Restful Team Interface"""

  @namespace.doc('create_new_team')
  @namespace.expect(create_team_model, validate=True)
  def post(self):
    user = current_user()

    if not user:
      return UNAUTHORIZED

    try:
      dbi.create(Team, {'name': api.payload['name']})
    except IntegrityError:
      logger.error('Team already exists for name: {}'.format(api.payload['name']))
      return TEAM_NAME_TAKEN
    except BaseException as e:
      logger.error('Error creating Team(name={}): {}'.format(api.payload['name'], e))
      return UNKNOWN_ERROR

    return TEAM_CREATION_SUCCESS