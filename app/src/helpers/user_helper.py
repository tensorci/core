from flask import request
from auth_util import unserialize_token
from src import dbi
from src.helpers.definitions import auth_header_name, cookie_name
from src.models import Token, User
from src.helpers import decode_url_encoded_str


def current_user():
  if request.cookies.get(cookie_name):
    # Request came from web (where we use a cookie), so decode the url-encoded cookie value
    user_token = decode_url_encoded_str(request.cookies.get(cookie_name))
  elif request.headers.get(auth_header_name):
    # Request came from CLI
    user_token = request.headers.get(auth_header_name)
  else:
    return None

  token_info = unserialize_token(user_token)

  if not token_info.get('token_id') or not token_info.get('secret'):
    return None

  token = dbi.find_one(Token, {
    'id': token_info['token_id'],
    'secret': token_info['secret']
  })

  if not token:
    return None

  return token.user