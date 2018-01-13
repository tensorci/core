from flask import request
from flask_restplus import Resource
from src.routes import namespace, api
from src.models import Provider, Dataset, Team, Repo, RepoProviderUser
from src import logger, dbi
from src.helpers.provider_user_helper import current_provider_user
from src.api_responses.errors import *
from src.api_responses.success import *
from src.services.dataset_services.create_dataset import CreateDataset
from src.helpers.provider_helper import parse_git_url
from slugify import slugify
from src.helpers import utcnow_to_ts


@namespace.route('/dataset')
class RestfulDataset(Resource):
  """Restful interface for the Dataset model"""

  @namespace.doc('create_dataset')
  def post(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    # Get refs to payload info
    payload = dict(request.form.items())
    git_url = payload.get('git_url')
    dataset_slug = payload.get('dataset_slug')

    provider_domain, team_name, repo_name = parse_git_url(git_url)

    # Find the provider by the passed domain
    provider = dbi.find_one(Provider, {'domain': provider_domain})

    if not provider:
      return PROVIDER_NOT_FOUND

    if provider != provider_user.provider:
      return PROVIDER_MISMATCH

    # Get dataset file
    files = dict(request.files.items()) or {}
    f = files.get('file')

    if not f:
      return NO_FILE_PROVIDED

    # Find repo for this team through provider
    team_slug = slugify(team_name, separator='-', to_lower=True)
    team = dbi.find_one(Team, {'slug': team_slug, 'provider': provider})

    if team:
      repo_slug = slugify(repo_name, separator='-', to_lower=True)
      repo = dbi.find_one(Repo, {'team': team, 'slug': repo_slug})
    else:
      repo_slug = None
      repo = None

    # Must register repo as a TensorCI repo before adding a dataset to it.
    if not repo:
      return REPO_NOT_REGISTERED

    repo_provider_user = dbi.find_one(RepoProviderUser, {
      'repo': repo,
      'provider_user': provider_user
    })

    if not repo_provider_user:
      return NOT_ASSOCIATED_WITH_REPO

    if repo_provider_user.role < RepoProviderUser.roles.MEMBER_WRITE:
      return INVALID_REPO_PERMISSIONS

    if not dataset_slug:
      dataset_slug = repo_slug

    # Check to see if a dataset already exists for this slug for this repo
    dataset = dbi.find_one(Dataset, {'repo': repo, 'slug': dataset_slug})

    if dataset:
      return DATASET_NAME_TAKEN

    try:
      # Create the dataset
      svc = CreateDataset(dataset_slug, repo=repo, fileobj=f)
      svc.perform()
    except BaseException as e:
      logger.error('Error creating Dataset(name={}, repo={}): {}'.format(dataset_slug, repo.slug, e))
      return DATASET_CREATION_FAILED

    return DATASET_CREATION_SUCCESS


@namespace.route('/datasets')
class RestfulDataset(Resource):
  """Restful interface for the Dataset model, continued"""

  @namespace.doc('get_datasets_for_repo')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    args = dict(request.args.items())
    team_slug = args.get('team')
    repo_slug = args.get('repo')

    if not team_slug:
      logger.error('No team provided during request for project datasets')
      return INVALID_INPUT_PAYLOAD

    if not repo_slug:
      logger.error('No repo provided during request for project datasets')
      return INVALID_INPUT_PAYLOAD

    team_slug = team_slug.lower()
    team = dbi.find_one(Team, {'slug': team_slug})

    if not team:
      return TEAM_NOT_FOUND

    repo_slug = repo_slug.lower()

    repo = [r for r in provider_user.repos() if r.team_id == team.id and r.slug == repo_slug]

    if not repo:
      return REPO_NOT_FOUND

    repo = repo[0]

    datasets = [{
      'name': d.name,
      'num_records': 100,  # Hardcoding for now
      'retrain_step_size': d.retrain_step_size,
      'last_train_record_count': d.last_train_record_count,
      'created_at': utcnow_to_ts(d.created_at)
    } for d in repo.datasets]

    return {'datasets': datasets}