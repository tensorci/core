from flask import request
from auth_util import unserialize_token
from src import dbi
from src.helpers.definitions import auth_header_name
from src.models import Session
from src.helpers import decode_url_encoded_str


def current_provider_user():
  if not request.headers.get(auth_header_name):
    return None

  token = decode_url_encoded_str(request.headers.get(auth_header_name))
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