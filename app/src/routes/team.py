from flask_restplus import Resource, fields
from src.routes import namespace, api
from src.helpers.user_helper import current_user
from src.api_responses.errors import *
from src.api_responses.success import *
from psycopg2 import IntegrityError
from slugify import slugify
from src import logger, dbi
from src.models import Team
from src.services.team_services.create_team import CreateTeam

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

    if dbi.find_one(Team, {'slug': slugify(api.payload['name'], separator='-', to_lower=True)}):
      return TEAM_NAME_TAKEN

    try:
      create_team_svc = CreateTeam(name=api.payload['name'], owner=user)
      create_team_svc.perform()
    except BaseException as e:
      logger.error('Error creating Team(name={}) and TeamUser(user.email={}): {}'.format(
        api.payload['name'], user.email, e))
      return UNKNOWN_ERROR

    return TEAM_CREATION_SUCCESS


@namespace.route('/teams')
class AllTeamsForUSer(Resource):
  """Endpoints related to all teams for a user"""

  @namespace.doc('get_all_teams_for_user')
  def get(self):
    user = current_user()

    if not user:
      return UNAUTHORIZED

    formatted_teams = [{
      'name': t.name,
      'slug': t.slug,
      'uid': t.uid
    } for t in user.teams()]

    return {'ok': True, 'data': formatted_teams}, 200