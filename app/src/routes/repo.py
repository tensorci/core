import boto3
from botocore.exceptions import ClientError
from flask import make_response, request
from flask_restplus import Resource, fields
from src.routes import namespace, api
from src.api_responses.errors import *
from src.api_responses.success import *
from src.helpers.provider_user_helper import current_provider_user
from src import logger, dbi
from slugify import slugify
from src.models import Team, Repo, RepoProviderUser, Provider
from src.helpers.provider_helper import parse_git_url
from src.services.team_services.create_team import CreateTeam


create_repo_model = api.model('Repo', {
  'repo_name': fields.String(required=True),
  'team_name': fields.String(required=True)
})

create_repos_model = api.model('Repos', {
  'repos': fields.List(fields.Nested(create_repo_model), required=True)
})

register_tensorci_repo = api.model('Repo', {
  'git_url': fields.String(required=True)
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

    # Group the new repos by team name
    teams_map = {}
    for data in new_repos:
      team_name = data.get('team_name')

      if team_name not in teams_map:
        teams_map[team_name] = []

      teams_map[team_name].append(data)

    # Upsert each team and each repo for that team
    for team_name, repos in teams_map.items():
      team_slug = slugify(team_name, separator='-', to_lower=True)

      # Upsert team
      team = dbi.find_one(Team, {'slug': team_slug, 'provider': provider})

      if team:
        team_is_new = False
      else:
        create_team_svc = CreateTeam(name=team_name, provider=provider)
        create_team_svc.perform()
        team = create_team_svc.team
        team_is_new = True

      for repo_info in repos:
        repo_name = repo_info.get('repo_name')
        repo_slug = slugify(repo_name, separator='-', to_lower=True)

        # Create new repo if team is new OR if repo doesn't exist yet
        if team_is_new or not dbi.find_one(Repo, {'team': team, 'slug': repo_slug}):
          repo = dbi.create(Repo, {
            'team': team,
            'name': repo_name
          })

          # Also create new RepoProviderUser when creating new Repo
          if team_name == provider_user.username:
            role = RepoProviderUser.roles.OWNER
          elif repo_info.get('is_admin'):
            role = RepoProviderUser.roles.ADMIN
          elif repo_info.get('has_push_access'):
            role = RepoProviderUser.roles.MEMBER_WRITE
          else:
            role = RepoProviderUser.roles.MEMBER_READ

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

  @namespace.doc('register_tensorci_repo')
  @namespace.expect(register_tensorci_repo, validate=True)
  def post(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    # Parse provided git url into components (domain, team, repo)
    git_url = api.payload['git_url']
    provider_domain, team_name, repo_name = parse_git_url(git_url)

    # Find the provider by the passed domain
    provider = dbi.find_one(Provider, {'domain': provider_domain})

    if not provider:
      return PROVIDER_NOT_FOUND

    if provider != provider_user.provider:
      return PROVIDER_MISMATCH

    # Check if team/repo/repo_provider_user already exists -- need to get
    # permissions for the repo_provider_user.
    team_slug = slugify(team_name, separator='-', to_lower=True)
    team = dbi.find_one(Team, {'slug': team_slug, 'provider': provider})
    repo = None
    repo_provider_user = None
    role = None

    # If the team already exists, check to see if the repo exists, too.
    if team:
      repo_slug = slugify(repo_name, separator='-', to_lower=True)
      repo = dbi.find_one(Repo, {'team': team, 'slug': repo_slug})

    # If the repo already exists, check to see if the repo_provider_user exists, too.
    if repo:
      repo_provider_user = dbi.find_one(RepoProviderUser, {
        'repo': repo,
        'provider_user': provider_user
      })

    # If repo_provider_user already exists, get his role.
    if repo_provider_user:
      role = repo_provider_user.role

    # If role couldn't be fetched via existing DB records, get it via the provider api.
    if role is None:
      provider_client = provider.client()(provider_user.access_token)
      repo_full_name = '{}/{}'.format(team_name, repo_name)

      try:
        external_repo = provider_client.get_repo(repo_full_name, lazy=False)
      except BaseException as e:
        logger.error('Error fetching external repo -- username={}, provider={}, repo_full_name={}'.format(
          provider_user.username, provider.name, repo_full_name))
        return INVALID_REPO_PERMISSIONS

      permissions = external_repo.permissions

      if team_name == provider_user.username:
        role = RepoProviderUser.roles.OWNER
      elif permissions.admin:
        role = RepoProviderUser.roles.ADMIN
      elif permissions.push:
        role = RepoProviderUser.roles.MEMBER_WRITE
      else:
        role = RepoProviderUser.roles.MEMBER_READ

    # Respond with invalid permissions if provider_user doesn't have write access to this repo.
    if role < RepoProviderUser.roles.MEMBER_WRITE:
      return INVALID_REPO_PERMISSIONS

    # At this point, we know the provider_user has (or will have) write to this TensorCI repo,
    # so upsert team, repo, and repo_provider_user for this provider_user.

    if not team:
      create_team_svc = CreateTeam(name=team_name, provider=provider)
      create_team_svc.perform()
      team = create_team_svc.team

    if not repo:
      repo = dbi.create(Repo, {'team': team, 'name': repo_name})

    if not repo_provider_user:
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
          permissions = repo.permissions

          formatted_repo = {
            'repo_name': repo.name,
            'team_name': team_name,
            'full_name': repo.full_name,
            'has_push_access': permissions.push,
            'is_admin': permissions.admin,
            'icon': team_icon,
            'in_use': repo.full_name in existing_repos_map
            # TODO: if in_use is True, return the endpoint to the repo's dashboard as well
          }

          resp['repos'].append(formatted_repo)

    return resp, 200


@namespace.route('/repo/model')
class FetchModel(Resource):
  """Fetch model file for repo from S3
  and stream it back to the client"""

  @namespace.doc('fetch_model')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    # Get refs to payload info
    payload = dict(request.form.items())
    git_url = payload.get('git_url')

    provider_domain, team_name, repo_name = parse_git_url(git_url)

    # Find the provider by the passed domain
    provider = dbi.find_one(Provider, {'domain': provider_domain})

    if not provider:
      return PROVIDER_NOT_FOUND

    if provider != provider_user.provider:
      return PROVIDER_MISMATCH

    # Find team and repo
    team_slug = slugify(team_name, separator='-', to_lower=True)
    team = dbi.find_one(Team, {'slug': team_slug, 'provider': provider})

    if team:
      repo_slug = slugify(repo_name, separator='-', to_lower=True)
      repo = dbi.find_one(Repo, {'team': team, 'slug': repo_slug})
    else:
      repo = None

    if not repo:
      return REPO_NOT_REGISTERED

    # Get the team's S3 bucket
    bucket = team.cluster.bucket

    # Download the file from S3 and stream it back to the client
    s3 = boto3.resource('s3')
    key = repo.model_file()

    if not key:
      return NO_MODEL_FILE_FOUND

    try:
      file = s3.Object(bucket.name, key).get()
    except ClientError as e:
      if e.response['Error']['Code'] == 'NoSuchKey':
        return NO_MODEL_FILE_FOUND
      else:
        raise e
    except BaseException as e:
      logger.error('Error fetching model file from S3 (bucket={}, key={}): {}'.format(bucket.name, key, e))
      return ERROR_PULLING_MODEL_FILE

    resp = make_response(file['Body'].read())
    resp.headers['Model-File-Type'] = repo.model_ext

    return resp