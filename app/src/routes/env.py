from flask import request
from flask_restplus import Resource, fields
from src.routes import namespace, api
from src import dbi, logger
from src.models import Team, RepoProviderUser, Env
from src.utils import clusters
from src.api_responses.errors import *
from src.api_responses.success import *
from src.helpers.provider_user_helper import current_provider_user

upsert_env_model = api.model('Env', {
  'uid': fields.String(required=False),
  'name': fields.String(required=True),
  'value': fields.String(required=True)
})

upsert_envs_model = api.model('Envs', {
  'team': fields.String(required=True),
  'repo': fields.String(required=True),
  'forCluster': fields.String(required=True),
  'envs': fields.List(fields.Nested(upsert_env_model), required=True)
})


@namespace.route('/envs')
class RestfulEnvs(Resource):
  """Restful interface for a repo's envs"""

  @namespace.doc('get_envs_for_repo')
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

    # Make sure this provider_user is associated with this repo
    repo_provider_user = dbi.find_one(RepoProviderUser, {
      'repo': repo,
      'provider_user': provider_user
    })

    if not repo_provider_user:
      return REPO_PROVIDER_USER_NOT_FOUND

    return repo.formatted_envs()

  @namespace.doc('upsert_envs_for_repo')
  @namespace.expect(upsert_envs_model, validate=True)
  def put(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    for_cluster = api.payload['forCluster']

    if for_cluster not in (clusters.TRAIN, clusters.API):
      return INVALID_INPUT_PAYLOAD

    team = dbi.find_one(Team, {'slug': api.payload['team'].lower()})

    if not team:
      return TEAM_NOT_FOUND

    repo = [r for r in provider_user.repos() if r.team_id == team.id and r.slug == api.payload['repo'].lower()]

    if not repo:
      return REPO_NOT_FOUND

    repo = repo[0]

    # Make sure this provider_user is associated with this repo
    repo_provider_user = dbi.find_one(RepoProviderUser, {
      'repo': repo,
      'provider_user': provider_user
    })

    if not repo_provider_user:
      return REPO_PROVIDER_USER_NOT_FOUND

    # Split env data into existing vs. new envs
    existing_env_map = {}
    new_env_data = []

    for data in (api.payload['envs'] or []):
      # Env exists if it has a uid
      if data.get('uid'):
        existing_env_map[data.get('uid')] = data
      else:
        new_env_data.append(data)

    existing_env_uids = existing_env_map.keys()

    try:
      # If there are any existing envs, fetch them in one query and update individually.
      if existing_env_uids:
        existing_envs = dbi.find_all(Env, {'uid': existing_env_uids})

        for env in existing_envs:
          # Get data to update env with (name & value)
          env_data = existing_env_map.get(env.uid)

          # Update env's name & value
          dbi.update(env, {
            'name': env_data.get('name'),
            'value': env_data.get('value')
          })

      # Create new envs
      for env_data in new_env_data:
        dbi.create(Env, {
          'repo': repo,
          'name': env_data.get('name'),
          'value': env_data.get('value'),
          'for_cluster': for_cluster
        })
    except BaseException as e:
      logger.error('Error upserting envs for Repo(uid={}) with error: {}'.format(repo.uid, e))
      return ERROR_UPSERTING_ENVS

    return {'envs': repo.formatted_envs(cluster=for_cluster)}


@namespace.route('/env')
class RestfulEnv(Resource):
  """Restful interface for a specific env"""

  @namespace.doc('delete_env')
  def delete(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    args = dict(request.args.items())
    env_uid = args.get('uid')

    env = dbi.find_one(Env, {'uid': env_uid})

    if not env:
      return ENV_NOT_FOUND

    repo = env.repo

    if not repo:
      return REPO_NOT_FOUND

    # Make sure this provider_user is associated with this repo
    repo_provider_user = dbi.find_one(RepoProviderUser, {
      'repo': repo,
      'provider_user': provider_user
    })

    if not repo_provider_user:
      return REPO_PROVIDER_USER_NOT_FOUND

    # TODO: Validate here (and on the FE) that this repo_provider_user has write access

    for_cluster = env.for_cluster

    # Delete the env
    try:
      dbi.delete(env)
    except BaseException as e:
      logger.error('Error deleting Env(uid={}) with error: {}'.format(env.uid, e))
      return ERROR_DELETING_ENV

    return {'envs': repo.formatted_envs(cluster=for_cluster)}