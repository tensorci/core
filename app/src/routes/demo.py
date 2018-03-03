import os
from flask import request
from flask_restplus import Resource
from operator import attrgetter
from src.routes import namespace
from src import dbi, logger
from src.models import ProviderUser
from src.api_responses.errors import *
from src.api_responses.success import *


@namespace.route('/demo/authenticate')
class DemoAuth(Resource):
  """Authenticate a demo user"""

  @namespace.doc('demo_auth')
  def get(self):
    # Get refs to payload info
    args = dict(request.args.items())
    token = args.get('token')

    if not token:
      logger.error('Bad Demo Login Attempt')
      return INVALID_INPUT_PAYLOAD

    # Make sure demo tokens match
    if token != os.environ.get('DEMO_TOKEN'):
      logger.error('Bad Demo Login Attempt')
      return UNAUTHORIZED

    # Log user in as Ben
    provider_user = dbi.find_one(ProviderUser, {'username': 'whittlbc'})

    provider = provider_user.provider
    teams = sorted([tpu.team for tpu in provider_user.team_provider_users], key=attrgetter('slug'))

    # "team" equal to the provider_user's username (i.e. whittlbc)
    username_team = None
    formatted_teams = []

    logger.info('Logging in as Demo User, whittlbc.')

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
      'user': {
        'username': provider_user.username,
        'icon': provider_user.icon
      },
      'teams': [username_team] + formatted_teams,
      'login_info': {
        'first_login': user.is_first_login(),
        'seen_basic_auth_prompt': user.seen_basic_auth_prompt
      }
    }

    return resp, 200
