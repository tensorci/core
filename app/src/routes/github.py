from flask import request, redirect, make_response
from flask_restplus import Resource
from src.routes import namespace, api
from src.api_responses.errors import *
from src.api_responses.success import *
from src import logger, dbi, db
from src.models import Provider, User
from github import Github
from src.helpers.definitions import auth_header_name


@namespace.route('/github/oauth_url')
class OAuthUrl(Resource):
  """
  Build GitHub OAuth url and return it to user for them to nav to
  """
  @namespace.doc('get_oauth_url')
  def get(self):
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

    # Get github provider and oauth class
    github = Provider.github()
    oauth = github.oauth()

    # Request access token for Github user
    access_token = oauth.get_access_token(code=temp_code)

    # Instantiate github api client library
    gh_client = Github(access_token)

    # Get current authed Github user and his/her username
    gh_user = gh_client.get_user()
    username = gh_user.login

    # Upsert user and update access_token
    user, is_new = dbi.upsert(User, {'provider': github, 'username': username})
    user = dbi.update(user, {'access_token': access_token})

    # Create new Session for user
    session = user.create_session()

    # Create redirect response with session token in the header
    resp = make_response(redirect('/'))
    resp.headers[auth_header_name] = session.token

    return resp