from flask import request
from flask_restplus import Resource
from src.routes import namespace, api
from src.api_responses.errors import *
from src.api_responses.success import *
from src.helpers.provider_user_helper import current_provider_user
from src import logger, dbi


@namespace.route('/repos')
class DashboardRepos(Resource):
  """
  Fetch repos for the dashboard for a provider_user
  """
  @namespace.doc('dashboard_repos')
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