import requests


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
    headers = self.build_headers()
    data = self.build_payload()

    if headers:
      args['headers'] = headers

    if data:
      args['json'] = data

    # Request access token from temp code
    resp = requests.post(url, **args)

    import code; code.interact(local=locals())

    if resp.status_code in (200, 201):
      try:
        json = resp.json() or {}
        self.access_token = json.get('access_token')
      except:
        pass

    return self

  def build_headers(self):
    headers = {}

    if self.integration.slug == 'github':
      headers['Accept'] = 'application/vnd.github.machine-man-preview+json'

    return headers

  def build_payload(self):
    payload = {
      'client_id': self.integration.client_id,
      'client_secret': self.integration.client_secret,
      'code': self.temp_code
    }

    if self.state:
      payload['state'] = self.state

    if self.redirect_uri:
      payload['redirect_uri'] = self.red

    return payload