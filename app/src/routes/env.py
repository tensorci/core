from flask import request
from flask_restplus import Resource, fields
from src.routes import namespace, api
from src import dbi, logger
from src.models import Team, RepoProviderUser, Env
from src.utils import clusters
from src.api_responses.errors import *
from src.api_responses.success import *
from src.utils.job_queue import job_queue
from src.helpers.provider_user_helper import current_provider_user
from src.services.env_services.update_deploy_env import UpdateDeployEnv

upsert_envs_model = api.model('Envs', {
  'team': fields.String(required=True),
  'repo': fields.String(required=True),
  'forCluster': fields.String(required=True)
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

    latest_envs = api.payload.get('envs', {})
    curr_envs = {e.name: e for e in repo.api_envs()}

    remove_env_names = [name for name, env in curr_envs.iteritems() if name not in latest_envs]
    update_envs_map = {}

    for name, value in latest_envs.iteritems():
      env = None

      # New Env Name
      if name not in curr_envs:
        env = dbi.create(Env, {
          'repo': repo,
          'name': name,
          'value': value,
          'for_cluster': for_cluster
        })

      # Name exists, but value changed
      elif curr_envs.get(name).value != value:
        env = dbi.update(curr_envs.get(name), {'value': value})

      # If change occured, register that
      if env:
        update_envs_map[env.name] = env.value

    # If env is for the API cluster and the repo has an active API deploy,
    # schedule an update to the env on that API cluster.
    if for_cluster == clusters.API and repo.deploy_name:
      update_envs_service = UpdateDeployEnv(repo_uid=repo.uid,
                                            updates=update_envs_map,
                                            removals=remove_env_names)

      job_queue.add(update_envs_service.perform)

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
    env_name = env.name

    # Delete the env
    try:
      dbi.delete(env)
    except BaseException as e:
      logger.error('Error deleting Env(uid={}) with error: {}'.format(env.uid, e))
      return ERROR_DELETING_ENV

    # If env var is for the API cluster and the repo has an active API deploy,
    # schedule the removal of this env var from that API cluster.
    if for_cluster == clusters.API and repo.deploy_name:
      job_queue.add(UpdateDeployEnv(repo_uid=repo.uid, removals=[env_name]).perform)

    return {'envs': repo.formatted_envs(cluster=for_cluster)}