import os
from flask import request, redirect
from flask_restplus import Resource
from src.routes import namespace, api
from src.api_responses.errors import *
from src.api_responses.success import *
from src import logger, dbi
from src.models import Provider, ProviderUser, User
from github import Github
from src.config import config
from src.helpers import url_encode_str, auth_util
from src.services.team_services.upsert_teams_from_orgs import UpsertTeamsFromOrgs


@namespace.route('/github/oauth_url')
class OAuthUrl(Resource):
  """
  Build GitHub OAuth url and return it to user for them to nav to
  """
  @namespace.doc('get_oauth_url')
  def get(self):
    args = dict(request.args.items())

    if not args.get('betaCode') or args.get('betaCode') != os.environ.get('BETA_ACCESS_CODE'):
      return INVALID_BETA_ACCESS_CODE

    oauth = Provider.github().oauth()

    return {'url': oauth.get_oauth_url()}


@namespace.route('/github/oauth')
class OAuthCallback(Resource):
  """
  Endpoint hit after a user authorizes the TensorCI GitHub OAuth App
  """
  @namespace.doc('oauth_user')
  def get(self):
    # Parse request args
    args = dict(request.args.items())
    temp_code = args.get('code')

    # Ensure temporary code is provided
    if not temp_code:
      logger.error('No temporary "code" arg provided in github OAuth callback.')
      return INVALID_OAUTH_TEMP_CODE

    # Get github provider and oauth class instance
    github = Provider.github()
    oauth = github.oauth()

    # Request access token for Github user
    access_token = oauth.get_access_token(code=temp_code)

    # Instantiate github api client library
    gh_client = Github(access_token)

    try:
      # Get current authed Github user and his/her username
      gh_user = gh_client.get_user()
      username = gh_user.login
    except BaseException as e:
      logger.error('Error getting authenticated Github user and username with error: {}'.format(e))
      return GITHUB_API_USER_ERROR

    # Attempt to find existing provider_user for username
    provider_user = dbi.find_one(ProviderUser, {
      'provider': github,
      'username': username
    })

    # If provider_user doesn't exist yet, create it (and upsert user)
    if not provider_user:
      try:
        # Get primary email for Github user so we can find his User record if it exists
        primary_email = [email.get('email') for email in gh_user.get_emails() if email.get('primary')]
      except BaseException as e:
        logger.error('Error reqeusting emails for Github user {}: {}'.format(username, e))
        return GITHUB_API_EMAIL_ERROR

      if not primary_email:
        logger.error('No primary email found for Github user with username: {}'.format(username))
        return GITHUB_API_EMAIL_ERROR

      primary_email = primary_email[0]

      # Upsert User for email
      user, is_new = dbi.upsert(User, {'email': primary_email})

      # Create provider user
      provider_user = dbi.create(ProviderUser, {
        'provider': github,
        'user': user,
        'username': username
      })

    # Update access token and icon
    provider_user = dbi.update(provider_user, {
      'access_token': access_token,
      'icon': gh_user.avatar_url
    })

    # Register a login for this user
    provider_user.user.register_login()

    try:
      # Create teams for provider_user
      UpsertTeamsFromOrgs(provider_user=provider_user).perform()
    except BaseException as e:
      logger.error('Error creating teams from github orgs for provider_user(id={}): {}'.format(provider_user.id, e))
      return ORG_TO_TEAM_CONVERSION_FAILED

    # Create new Session for provider_user
    session = provider_user.create_session()

    # Create redirect response with session token
    token = auth_util.serialize_token(session.id, session.token)

    return redirect('{}/oauth_redirect?auth={}&username={}&icon={}'.format(
      config.DASH_URL, url_encode_str(token), provider_user.username, provider_user.icon))