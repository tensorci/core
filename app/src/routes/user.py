from flask_restplus import Resource, fields
from src.routes import namespace, api
from src import dbi, logger
from src.helpers import auth_util
from src.api_responses.errors import *
from src.api_responses.success import *
from src.helpers.provider_user_helper import current_provider_user

set_password_model = api.model('User', {
  'password': fields.String(required=True)
})


@namespace.route('/user/password')
class UserPassword(Resource):
  """Restful interface for a user's basic auth password"""

  @namespace.doc('set_user_password')
  @namespace.expect(set_password_model, validate=True)
  def put(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    user = provider_user.user

    if not user:
      return USER_NOT_FOUND

    try:
      # update the user's hashed_pw
      # dbi.update(user, {'hashed_pw': auth_util.hash_pw(api.payload['password'])})
      dbi.update(user, {'hashed_pw': api.payload['password']})
    except BaseException as e:
      logger.error('Error updating hashed password for User(id={}): {}'.format(user.id, e))
      return UNKNOWN_ERROR

    return UPDATE_USER_PW_SUCCESS

  @namespace.doc('get_user_password')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    user = provider_user.user

    if not user:
      return USER_NOT_FOUND

    return {'pw': user.hashed_pw}