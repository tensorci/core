from urlparse import urlparse
import re


def parse_git_url(url):
  result = urlparse(url)

  provider_domain = result.netloc.split('@').pop()
  team_name = None
  repo_name = None

  path_match = re.match('/(.*).git', result.path)

  if path_match:
    path = path_match.groups()[0]
    team_name, repo_name = path.split('/')

  return provider_domain, team_name, repo_name