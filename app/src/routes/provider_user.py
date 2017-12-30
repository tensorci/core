from flask_restplus import Resource, fields
from src.routes import namespace, api
from src.api_responses.errors import *
from src.api_responses.success import *
from src.helpers.definitions import auth_header_name
from src import logger, dbi
from src.models import ProviderUser, Provider
from src.helpers.provider_user_helper import current_provider_user
from src.helpers import auth_util

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
    username = api.payload['username'].lower()
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

    # Fail if password from payload doesn't equal the user's password
    if not auth_util.verify_pw(user.hashed_pw or '', pw):
      return AUTHENTICATION_FAILED

    # Create a new session and pass the session token back through a header
    session = provider_user.create_session()
    token = auth_util.serialize_token(session.id, session.token)

    return {'ok': True, 'message': 'Login Successful'}, 200, {auth_header_name: token}


@namespace.route('/provider_user/available_repos')
class AvailableRepos(Resource):
  """
  Get all available repos for the provider_user through the provider
  (e.g. get all Github repos for a Github user)
  """

  @namespace.doc('get_available_provider_repos')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    try:
      available_repos = provider_user.available_repos()
    except BaseException as e:
      logger.error('Error fetching available repos for provider_user(uid={}): {}'.format(provider_user.uid, e))
      return ERROR_FETCHING_AVAILABLE_REPOS

    resp = {'repos': []}

    if available_repos:
      existing_repos = provider_user.repos()
      existing_repos_map = {r.full_name().lower(): True for r in existing_repos}

      available_teams_map = {}
      for r in available_repos:
        team_slug = r.owner.login.lower()

        if team_slug not in available_teams_map:
          available_teams_map[team_slug] = {}

        available_teams_map[team_slug][r.name] = r

      sorted_available_teams = sorted(available_teams_map.keys())

      for team_slug in sorted_available_teams:
        team_repos_map = available_teams_map[team_slug]
        team_icon = team_repos_map.values()[0].owner.avatar_url
        sorted_team_repos = sorted(team_repos_map.keys())

        for repo_slug in sorted_team_repos:
          repo = team_repos_map[repo_slug]

          formatted_repo = {
            'full_name': repo.full_name,
            'icon': team_icon,
            'in_use': repo.full_name in existing_repos_map
            # TODO: if in_use is True, return the url to the repo's dashboard as well
          }

          resp['repos'].append(formatted_repo)

    return resp, 200