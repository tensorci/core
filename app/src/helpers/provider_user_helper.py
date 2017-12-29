from flask import request
from auth_util import unserialize_token
from src import dbi
from src.helpers.definitions import auth_header_name, cookie_name
from src.models import ProviderUser, Session
from src.helpers import decode_url_encoded_str


def current_provider_user():
  # Get token by cookie or header (cookie has priority)
  if request.cookies.get(cookie_name):
    token = decode_url_encoded_str(request.cookies.get(cookie_name))
  elif request.headers.get(auth_header_name):
    token = request.headers.get(auth_header_name)
  else:
    return None

  if not token:
    return None

  session_info = unserialize_token(token)

  if not session_info.get('session_id') or not session_info.get('secret'):
    return None

  session = dbi.find_one(Session, {
    'id': session_info['session_id'],
    'token': session_info['secret']
  })

  if not session:
    return None

  return session.provider_user