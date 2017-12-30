from flask_restplus import Resource, fields
from src.routes import namespace, api
from src.api_responses.errors import *
from src.api_responses.success import *
from src.helpers.provider_user_helper import current_provider_user
from src import logger, dbi
from slugify import slugify
from src.models import Team, Repo, RepoProviderUser

create_repo_model = api.model('Repo', {
  'repo_name': fields.String(required=True),
  'team_name': fields.String(required=True)
})

create_repos_model = api.model('Repos', {
  'repos': fields.List(fields.Nested(create_repo_model), required=True)
})


@namespace.route('/repos')
class RestfulRepos(Resource):
  """
  RESTful interface to TensorCI repos
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

  @namespace.doc('create_tensorci_repos')
  @namespace.expect(create_repos_model, validate=True)
  def post(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    provider = provider_user.provider

    # Get the repos to-be-created from the payload
    new_repos = api.payload['repos']

    # Group the new repos by team
    teams_map = {}
    for data in new_repos:
      team_name = data.get('team_name')

      if team_name not in teams_map:
        teams_map[team_name] = []

      teams_map[team_name].append(data.get('repo_name'))

    # Upsert each team and each repo for that team
    for team_name, repo_names in teams_map.items():
      team, team_is_new = dbi.upsert(Team, {
        'name': team_name,
        'provider': provider
      })

      for repo_name in repo_names:
        repo_slug = slugify(repo_name, separator='-', to_lower=True)

        # Create new repo if team is new OR if repo doesn't exist yet
        if team_is_new or not dbi.find_one(Repo, {'team': team, 'slug': repo_slug}):
          repo = dbi.create(Repo, {
            'team': team,
            'name': repo_name
          })

          # Also create new RepoProviderUser when creating new Repo
          # his/her role will depend on
          if repo.owner.login == provider_user.username:
            role = RepoProviderUser.roles.OWNER
          elif repo.permissions.admin:
            role = RepoProviderUser.roles.ADMIN
          else:
            # TODO: ideally, you shouldn't be able to create a TensorCI repo from a Github repo if
            # you're neither the owner or an admin...
            role = RepoProviderUser.roles.MEMBER

          dbi.create(RepoProviderUser, {
            'repo': repo,
            'provider_user': provider_user,
            'role': role
          })

    return REPOS_CREATION_SUCCESS


@namespace.route('/repo/register')
class RegisterRepo(Resource):
  """
  Register repo from a provider as a TensorCI repo
  """

  @namespace.doc('create_tensorci_repo')
  @namespace.expect(create_repo_model, validate=True)
  def post(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    team_name = api.payload['team_name']
    repo_name = api.payload['repo_name']
    provider = provider_user.provider

    team, team_is_new = dbi.upsert(Team, {
      'name': team_name,
      'provider': provider
    })

    repo_slug = slugify(repo_name, separator='-', to_lower=True)

    # Create new repo if team is new OR if repo doesn't exist yet
    if team_is_new or not dbi.find_one(Repo, {'team': team, 'slug': repo_slug}):
      repo = dbi.create(Repo, {
        'team': team,
        'name': repo_name
      })

      # Also create new RepoProviderUser when creating new Repo
      # his/her role will depend on
      if repo.owner.login == provider_user.username:
        role = RepoProviderUser.roles.OWNER
      elif repo.permissions.admin:
        role = RepoProviderUser.roles.ADMIN
      else:
        # TODO: ideally, you shouldn't be able to create a TensorCI repo from a Github repo if
        # you're neither the owner or an admin...
        role = RepoProviderUser.roles.MEMBER

      dbi.create(RepoProviderUser, {
        'repo': repo,
        'provider_user': provider_user,
        'role': role
      })

    return REPO_CREATION_SUCCESS


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
        owner = team_repos_map.values()[0].owner
        team_name = owner.login
        team_icon = owner.avatar_url
        sorted_team_repos = sorted(team_repos_map.keys())

        for repo_slug in sorted_team_repos:
          repo = team_repos_map[repo_slug]

          formatted_repo = {
            'repo_name': repo.name,
            'team_name': team_name,
            'full_name': repo.full_name,
            'icon': team_icon,
            'in_use': repo.full_name in existing_repos_map
            # TODO: if in_use is True, return the endpoint to the repo's dashboard as well
          }

          resp['repos'].append(formatted_repo)

    return resp, 200