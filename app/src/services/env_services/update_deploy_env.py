from src import dbi, logger
from src.models import Repo, Env
from src.utils import kubectl


class UpdateDeployEnv(object):

  def __init__(self, repo_uid=None, env_uids=None):
    self.repo_uid = repo_uid
    self.env_uids = env_uids or []

  def perform(self):
    repo = dbi.find_one(Repo, {'uid': self.repo_uid})
    cluster_name = repo.team.cluster.name
    deploy_name = repo.deploy_name

    if not deploy_name:
      logger.error('Not updating envs for Repo(uid={}) -- No deploy_name on repo.'.format(self.repo_uid))
      return

    envs = dbi.find_all(Env, {'uid': self.env_uids})

    if not envs:
      logger.error('Not updating envs for Repo(uid={}) -- No envs found for uids: {}.'.format(
        self.repo_uid, self.env_uids))
      return

    success = kubectl.set_envs(deployment_name=deploy_name,
                               envs=envs,
                               context=cluster_name,
                               cluster=cluster_name)

    if not success:
      logger.error('Failed to update envs for Repo(uid={}): {}'.format(self.repo_uid, self.env_uids))