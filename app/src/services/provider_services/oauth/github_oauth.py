import os
import requests
from src import logger
from src.config import config
from urllib import urlencode
from urlparse import parse_qs


class GithubOAuth(object):
  CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
  CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')
  SCOPES = ('user', 'repo')

  def __init__(self, provider=None):
    self.provider = provider
    self.provider_url = self.provider.url()
    self.oauth_url = self.provider_url + '/login/oauth/authorize'
    self.access_token_url = self.provider_url + '/login/oauth/access_token'
    self.redirect_uri = config.CORE_URL + '/github/oauth'

  def get_access_token(self, code=None):
    payload = {
      'client_id': self.CLIENT_ID,
      'client_secret': self.CLIENT_SECRET,
      'redirect_uri': self.redirect_uri,
      'code': code
    }

    try:
      resp = requests.post(self.access_token_url, params=payload)
    except BaseException as e:
      logger.error('Requesting access token for Github user failed: {}'.format(e))
      return None

    content = resp.content
    content = parse_qs(content) or {}
    access_token = content.get('access_token')

    if not access_token:
      return None

    return access_token[0]

  def get_oauth_url(self):
    params = {
      'client_id': self.CLIENT_ID,
      'redirect_uri': self.redirect_uri,
      'scope': ','.join(self.SCOPES)
    }

    return self.oauth_url + '?' + urlencode(params)