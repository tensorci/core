import boto3
from botocore.exceptions import ClientError
from flask import make_response, request
from flask_restplus import Resource, fields
from src.routes import namespace, api
from src.api_responses.errors import *
from src.api_responses.success import *
from src.helpers.provider_user_helper import current_provider_user
from src import logger, dbi, db
from sqlalchemy.orm import joinedload
from src.helpers import auth_util, utcnow_to_ts
from slugify import slugify
from src.models import Team, Repo, RepoProviderUser, Provider, TeamProviderUser, Deployment
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

regen_secret_model = api.model('Repo', {
  'team': fields.String(required=True),
  'repo': fields.String(required=True)
})


@namespace.route('/repos')
class RestfulRepos(Resource):
  """
  RESTful interface to TensorCI repos
  """
  @namespace.doc('get_tensorci_repos_for_provider_user_for_team')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    # Parse input info
    args = dict(request.args.items())
    team_slug = args.get('team')
    repo_slug = args.get('repo')
    with_deployments = args.get('with_deployments')

    # Get team
    if not team_slug:
      logger.error('No team provided during request for team repos')
      return INVALID_INPUT_PAYLOAD

    team_slug = team_slug.lower()
    team = dbi.find_one(Team, {'slug': team_slug})

    if not team:
      return TEAM_NOT_FOUND

    # Get all repos for team, ordered by slug
    repos = [r for r in provider_user.repos() if r.team_id == team.id]

    formatted_repos = [{
      'slug': repo.slug,
      'name': repo.name
    } for repo in repos]

    formatted_repos.sort(key=lambda x: x['slug'])

    resp = {
      'repos': formatted_repos
    }

    if not with_deployments or not formatted_repos:
      return resp

    # if repo_slug provided to get deployments for, try to find/use this repo.
    if repo_slug:
      repo = [r for r in repos if r.slug == repo_slug.lower()]

      # If repo not part of team, just return early
      if not repo:
        return resp
    else:
      # if no repo_slug provided, just use the first repo ordered by slug
      repo = [r for r in repos if r.slug == formatted_repos[0]['slug']]

    repo = repo[0]

    resp['repo'] = repo.slug

    # TODO: Consolidate the following copypasta from /api/deployments

    resp['deployments'] = []

    deployments = db.session.query(Deployment) \
      .options(joinedload(Deployment.commit)) \
      .filter_by(repo_id=repo.id) \
      .order_by(Deployment.intent_updated_at).all()

    if not deployments:
      return resp

    deployments.reverse()

    for d in deployments:
      commit = d.commit
      train_job = d.train_job

      if train_job:
        train_duration_sec = train_job.duration().seconds
      else:
        train_duration_sec = 0

      resp['deployments'].append({
        'uid': d.uid,
        'readable_status': d.readable_status(),
        'failed': d.failed,
        'succeeded': d.succeeded(),
        'date': utcnow_to_ts(d.intent_updated_at),
        'train_duration_sec': train_duration_sec,
        'commit': {
          'sha': commit.sha,
          'branch': commit.branch,
          'message': commit.message,
          'author': commit.author,
          'author_icon': commit.author_icon
        }
      })

    return resp

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

    args = dict(request.args.items())
    team_slug = args.get('team')

    if not team_slug:
      logger.error('No team provided during request for available repos')
      return INVALID_INPUT_PAYLOAD

    team_slug = team_slug.lower()
    team = dbi.find_one(Team, {'slug': team_slug})

    if not team:
      return TEAM_NOT_FOUND

    team_provider_user = dbi.find_one(TeamProviderUser, {
      'team': team,
      'provider_user': provider_user
    })

    if not team_provider_user:
      return UNAUTHORIZED

    try:
      available_repos = provider_user.available_repos()
    except BaseException as e:
      logger.error('Error fetching available repos for provider_user(uid={}): {}'.format(provider_user.uid, e))
      return ERROR_FETCHING_AVAILABLE_REPOS

    resp = {'repos': []}

    if not available_repos:
      return resp, 200

    avail_team_repos = [r for r in available_repos if r.owner.login.lower() == team_slug]

    if not avail_team_repos:
      return resp, 200

    existing_repos_map = {r.slug: True for r in team.repos}

    for r in avail_team_repos:
      permissions = r.permissions

      formatted_repo = {
        'name': r.name,
        'slug': r.name.lower(),
        'creatable': permissions.admin or permissions.push,
        'exists': r.name.lower() in existing_repos_map
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

    # Get refs to args info
    args = dict(request.args.items())
    git_url = args.get('git_url')

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


@namespace.route('/repo/creds')
class GetRepoCreds(Resource):
  """
  Fetch client_id & client_secret for repo
  """
  @namespace.doc('get_repo_creds')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    args = dict(request.args.items())
    team_slug = args.get('team')
    repo_slug = args.get('repo')

    if not team_slug:
      logger.error('No team provided during request for repo credentials')
      return INVALID_INPUT_PAYLOAD

    if not repo_slug:
      logger.error('No repo provided during request for repo credentials')
      return INVALID_INPUT_PAYLOAD

    team_slug = team_slug.lower()
    repo_slug = repo_slug.lower()

    team = dbi.find_one(Team, {'slug': team_slug})

    if not team:
      return TEAM_NOT_FOUND

    repo = [r for r in provider_user.repos() if r.team_id == team.id and r.slug == repo_slug]

    if not repo:
      return REPO_NOT_FOUND

    repo = repo[0]

    resp = {
      'client_id': repo.client_id,
      'client_secret': repo.client_secret
    }

    return resp


@namespace.route('/repo/secret')
class GetRepoCreds(Resource):
  """
  Regenerate client_secret for repo
  """

  @namespace.doc('regen_client_secret')
  @namespace.expect(regen_secret_model, validate=True)
  def put(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    team_slug = api.payload['team'].lower()
    repo_slug = api.payload['repo'].lower()

    team = dbi.find_one(Team, {'slug': team_slug})

    if not team:
      return TEAM_NOT_FOUND

    repo = [r for r in provider_user.repos() if r.team_id == team.id and r.slug == repo_slug]

    if not repo:
      return REPO_NOT_FOUND

    repo = repo[0]

    # Generate new secret
    new_secret = auth_util.fresh_secret()

    # Update the repo with the new client_secret
    dbi.update(repo, {'client_secret': new_secret})

    # Return with the new secret
    resp = {
      'client_secret': new_secret
    }

    return resp

