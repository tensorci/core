import os
from abstract_integration import AbstractIntegration
from github import Github


class GH(AbstractIntegration):
  slug = 'github'
  client_id = os.environ.get('GITHUB_CLIENT_ID')
  client_secret = os.environ.get('GITHUB_CLIENT_SECRET')

  def __init__(self, prediction_integration=None):
    super(GH, self).__init__(prediction_integration)
    self.client = Github()

  def get_installation(self, id):
    return self.client.get_installation(id)

  def repo_urls_for_installation(self, installation):
    repos = installation.get_repos()

    for repo in repos:
      pass