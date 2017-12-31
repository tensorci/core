from flask_restplus import Resource, fields
from src.routes import namespace, api
from src.api_responses.errors import *
from src.api_responses.success import *
from src.helpers.definitions import auth_header_name
from src import logger, dbi
from src.models import ProviderUser, Provider
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

    # Fail if password from payload doesn't equal the user's password
    if not auth_util.verify_pw(user.hashed_pw or '', pw):
      return AUTHENTICATION_FAILED

    # Create a new session and pass the session token back through a header
    session = provider_user.create_session()
    token = auth_util.serialize_token(session.id, session.token)

    return {'ok': True, 'message': 'Login Successful'}, 200, {auth_header_name: token}