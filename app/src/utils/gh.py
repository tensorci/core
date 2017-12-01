from github import Github
from urlparse import urlparse

gh = Github()


def fetch_git_repo(repo_url):
  parsed = urlparse(repo_url)
  full_repo_name = parsed.path

  if full_repo_name.startswith('/'):
    full_repo_name = full_repo_name[1:]

  if full_repo_name.endswith('.git'):
    full_repo_name = full_repo_name[:-4]

  return gh.get_repo(full_repo_name, lazy=False)