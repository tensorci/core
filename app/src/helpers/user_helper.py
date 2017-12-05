from flask import request
from auth_util import unserialize_token
from src import dbi
from src.helpers.definitions import auth_header_name
from src.models import Token, User
from src.helpers import decode_url_encoded_str


def current_user():
  return dbi.find_one(User, {'email': 'benwhittle31@gmail.com'})

  user_token = request.cookies.get('tensorci-user') or request.headers.get(auth_header_name)

  if not user_token:
    return None

  token_info = unserialize_token(decode_url_encoded_str(user_token))

  if not token_info.get('token_id') or not token_info.get('secret'):
    return None

  token = dbi.find_one(Token, {
    'id': token_info['token_id'],
    'secret': token_info['secret']
  })

  if not token:
    return None

  return token.user