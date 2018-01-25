from flask import request
from flask_restplus import Resource, fields
from src.routes import namespace, api
from src.models import Provider, Dataset, Team, Repo, RepoProviderUser
from src import logger, dbi
from src.helpers.provider_user_helper import current_provider_user
from src.api_responses.errors import *
from src.api_responses.success import *
from src.services.dataset_services.create_dataset import CreateDataset
from src.helpers.provider_helper import parse_git_url
from slugify import slugify
from src.utils import dataset_db
from src.helpers import utcnow_to_ts

update_dataset_model = api.model('Dataset', {
  'uid': fields.String(required=True),
  'retrainStepSize': fields.Integer(required=True)
})


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

  @namespace.doc('update_dataset')
  @namespace.expect(update_dataset_model, validate=True)
  def put(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    # Find dataset for provided uid
    dataset = dbi.find_one(Dataset, {'uid': api.payload['uid']})

    if not dataset:
      return DATASET_NOT_FOUND

    # Make sure this provider_user is associated with this dataset (through repo)
    repo_provider_user = dbi.find_one(RepoProviderUser, {
      'repo': dataset.repo,
      'provider_user': provider_user
    })

    if not repo_provider_user:
      return REPO_PROVIDER_USER_NOT_FOUND

    # Make sure repo_provider_user has write access to this repo (and therefore, its datasets)
    if not repo_provider_user.has_write_access():
      return UNAUTHORIZED

    # Update dataset's retrain_step_size
    dbi.update(dataset, {'retrain_step_size': api.payload['retrainStepSize']})

    return DATASET_SUCCESSFULLY_UPDATED

  @namespace.doc('delete_dataset')
  def delete(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    args = dict(request.args.items())
    dataset_uid = args.get('uid')

    if not dataset_uid:
      return INVALID_INPUT_PAYLOAD

    # Find dataset for provided uid
    dataset = dbi.find_one(Dataset, {'uid': dataset_uid})

    if not dataset:
      return DATASET_NOT_FOUND

    # Make sure this provider_user is associated with this dataset (through repo)
    repo_provider_user = dbi.find_one(RepoProviderUser, {
      'repo': dataset.repo,
      'provider_user': provider_user
    })

    if not repo_provider_user:
      return REPO_PROVIDER_USER_NOT_FOUND

    # Make sure repo_provider_user has write access to this repo (and therefore, its datasets)
    if not repo_provider_user.has_write_access():
      return UNAUTHORIZED

    try:
      # Get ref to the table name
      table_name = dataset.table()

      # Hard delete the dataset record
      dbi.delete(dataset)

      # Drop the dataset table
      dataset_db.drop_table(table_name)
    except BaseException as e:
      logger.error('Error deleting Dataset(uid={}) and dropping table with error: {}'.format(dataset_uid, e))
      return DATASET_DELETION_FAILED

    return DATASET_SUCCESSFULLY_DELETED


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

    # Make sure this provider_user is associated with this dataset (through repo)
    repo_provider_user = dbi.find_one(RepoProviderUser, {
      'repo': repo,
      'provider_user': provider_user
    })

    if not repo_provider_user:
      return REPO_PROVIDER_USER_NOT_FOUND

    datasets = [{
      'name': d.name,
      'uid': d.uid,
      'num_records': dataset_db.record_count(table=d.table()),
      'retrain_step_size': d.retrain_step_size,
      'last_train_record_count': d.last_train_record_count,
      'created_at': utcnow_to_ts(d.created_at),
      'has_write_access': repo_provider_user.has_write_access(),
      'preview': dataset_db.sample(table=d.table(), limit=5)
    } for d in repo.datasets]

    return {'datasets': datasets}


# ** DEPRECATED **
@namespace.route('/dataset/preview')
class RestfulDataset(Resource):
  """Fetch preview for dataset"""

  @namespace.doc('fetch_preview_for_dataset')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    args = dict(request.args.items())
    dataset_uid = args.get('uid')

    if not dataset_uid:
      return INVALID_INPUT_PAYLOAD

    # Find dataset for provided uid
    dataset = dbi.find_one(Dataset, {'uid': dataset_uid})

    if not dataset:
      return DATASET_NOT_FOUND

    # Make sure this provider_user is associated with this dataset (through repo)
    repo_provider_user = dbi.find_one(RepoProviderUser, {
      'repo': dataset.repo,
      'provider_user': provider_user
    })

    if not repo_provider_user:
      return REPO_PROVIDER_USER_NOT_FOUND

    preview_records = dataset_db.sample(table=dataset.table(), limit=10)

    return {'preview': preview_records}