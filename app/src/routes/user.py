from flask_restplus import Resource, fields
from src.routes import namespace, api
from src.api_responses.errors import *
from src.api_responses.success import *
from src.helpers.definitions import auth_header_name
from src import logger, dbi
from src.models import User, Token
from src.helpers import auth_util

user_login_model = api.model('User', {
  'email': fields.String(required=True),
  'password': fields.String(required=True)
})


# TODO: Make this for both CLI usage as well as web app. Right now it's only for CLI
@namespace.route('/user/login')
class UserLogin(Resource):
  """Login as a user"""

  @namespace.doc('user_login')
  @namespace.expect(user_login_model, validate=True)
  def post(self):
    # Get email, password from payload
    email = api.payload['email'].lower()
    pw = api.payload['password']

    # Attempt to find user by email
    user = dbi.find_one(User, {'email': email})

    # Fail if user not found
    if not user:
      return AUTHENTICATION_FAILED

    # Fail if password doesn't equal their hashed password
    if not auth_util.verify_pw(user.hashed_pw or '', pw):
      return AUTHENTICATION_FAILED

    # Create a new secret and a new token
    secret = auth_util.fresh_secret()
    token = dbi.create(Token, {'user': user, 'secret': secret})

    header_token = auth_util.serialize_token(token.id, secret)
    response_headers = {auth_header_name: header_token}

    # Respond with success and pass the token secret back inside a header
    return {'ok': True, 'message': 'Login Successful'}, 200, response_headers