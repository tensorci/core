from flask_restplus import Resource, fields
from src.routes import namespace, api
from src.api_responses.errors import *
from src.api_responses.success import *
from src.helpers.definitions import auth_header_name
from src import logger, dbi
from src.models import ProviderUser, Provider, TeamProviderUser
from src.helpers import auth_util
from src.helpers.provider_user_helper import current_provider_user
from operator import attrgetter
from src.config import config

provider_user_login_model = api.model('User', {
  'username': fields.String(required=True),
  'password': fields.String(required=True),
  'provider': fields.String(required=True)
})


@namespace.route('/provider_user/login')
class ProviderUserLogin(Resource):
  """Login as a provider_user"""

  @namespace.doc('provider_user_login')
  @namespace.expect(provider_user_login_model, validate=True)
  def post(self):
    # Get important info from payload
    username = api.payload['username']
    pw = api.payload['password']
    provider_slug = api.payload['provider']

    # Get provider for slug
    provider = dbi.find_one(Provider, {'slug': provider_slug})

    if not provider:
      return PROVIDER_NOT_FOUND

    # Get provider_user by provider/username
    provider_user = dbi.find_one(ProviderUser, {
      'provider': provider,
      'username': username
    })

    if not provider_user:
      return AUTHENTICATION_FAILED

    # Get user for provider_user
    user = provider_user.user

    # Ensure user has even set their basic auth pw...
    if not user.hashed_pw:
      return AUTHENTICATION_FAILED

    # Fail if password from payload doesn't equal the user's password
    # if not auth_util.verify_pw(user.hashed_pw or '', pw):
    if user.hashed_pw != pw:
      return AUTHENTICATION_FAILED

    # Create a new session and pass the session token back through a header
    session = provider_user.create_session()
    token = auth_util.serialize_token(session.id, session.token)

    # Register user login
    user.register_login()

    return {'ok': True, 'message': 'Login Successful'}, 200, {auth_header_name: token}


@namespace.route('/provider_user/storage_info')
class GetLocalStorageInfo(Resource):
  """Get local storage info for provider user"""

  @namespace.doc('get_local_storage_info')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    provider = provider_user.provider
    teams = sorted([tpu.team for tpu in provider_user.team_provider_users], key=attrgetter('slug'))

    # "team" equal to the provider_user's username (i.e. whittlbc)
    username_team = None
    formatted_teams = []

    for t in teams:
      formatted_team = {
        'name': t.name,
        'slug': t.slug,
        'icon': t.icon,
        'provider': provider.slug
      }

      if t.slug == provider_user.username:
        username_team = formatted_team
      else:
        formatted_teams.append(formatted_team)

    user = provider_user.user

    resp = {
      'teams': [username_team] + formatted_teams,
      'login_info': {
        'first_login': user.is_first_login(),
        'seen_basic_auth_prompt': user.seen_basic_auth_prompt
      }
    }

    return resp, 200


@namespace.route('/provider_user/logout_url')
class GetLogoutUrl(Resource):
  """Get logout url"""

  @namespace.doc('get_logout_url')
  def get(self):
    return {'url': config.MARKETING_URL}