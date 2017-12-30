from flask_restplus import Resource
from src.routes import namespace, api
from src.api_responses.errors import *
from src.api_responses.success import *
from src.helpers.provider_user_helper import current_provider_user
from src import logger, dbi


@namespace.route('/repos')
class GetRepos(Resource):
  """
  Fetch TensorCI repos for a provider_user
  """
  @namespace.doc('get_tensorci_repos_for_provider_user')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    repos = provider_user.repos()

    formatted_repos = []
    for repo in repos:
      # TODO: format repo how you need it
      formatted_repo = {'slug': repo.slug}
      formatted_repos.append(formatted_repo)

    return {'repos': formatted_repos}


@namespace.route('/repos/available')
class GetAvailableRepos(Resource):
  """
  Get all available repos for the provider_user through the provider
  (e.g. get all Github repos for a Github user)
  """

  @namespace.doc('get_available_provider_repos')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    try:
      available_repos = provider_user.available_repos()
    except BaseException as e:
      logger.error('Error fetching available repos for provider_user(uid={}): {}'.format(provider_user.uid, e))
      return ERROR_FETCHING_AVAILABLE_REPOS

    resp = {'repos': []}

    if available_repos:
      existing_repos = provider_user.repos()
      existing_repos_map = {r.full_name().lower(): True for r in existing_repos}

      available_teams_map = {}
      for r in available_repos:
        team_slug = r.owner.login.lower()

        if team_slug not in available_teams_map:
          available_teams_map[team_slug] = {}

        available_teams_map[team_slug][r.name] = r

      sorted_available_teams = sorted(available_teams_map.keys())

      for team_slug in sorted_available_teams:
        team_repos_map = available_teams_map[team_slug]
        team_icon = team_repos_map.values()[0].owner.avatar_url
        sorted_team_repos = sorted(team_repos_map.keys())

        for repo_slug in sorted_team_repos:
          repo = team_repos_map[repo_slug]

          formatted_repo = {
            'full_name': repo.full_name,
            'icon': team_icon,
            'in_use': repo.full_name in existing_repos_map
            # TODO: if in_use is True, return the url to the repo's dashboard as well
          }

          resp['repos'].append(formatted_repo)

    return resp, 200