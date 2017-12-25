import requests
from urlparse import parse_qs


class OAuthTokenExchange(object):

  def __init__(self, integration=None, temp_code=None, redirect_uri=None, state=None):
    self.integration = integration
    self.temp_code = temp_code
    self.redirect_uri = redirect_uri
    self.state = state
    self.access_token = None

  def perform(self):
    # Get url and build payload for integration
    url = self.integration.oauth_token_exchange_url
    args = {}
    data = self.build_payload()

    if data:
      args['params'] = data

    # Request access token from temp code
    resp = requests.post(url, **args)

    if resp.status_code not in (200, 201):
      return self

    content = resp.content

    if not content:
      return self

    content = parse_qs(content) or {}
    access_token = content.get('access_token')

    if access_token:
      self.access_token = access_token[0]

    return self

  def build_payload(self):
    payload = {
      'client_id': self.integration.client_id,
      'client_secret': self.integration.client_secret,
      'code': self.temp_code
    }

    if self.state:
      payload['state'] = self.state

    if self.redirect_uri:
      payload['redirect_uri'] = self.redirect_uri

    return payload