from src import dbi, logger
from src.models import Repo, Env
from src.utils import kubectl


class UpdateDeployEnv(object):

  def __init__(self, repo_uid=None, updates=None, removals=None):
    self.repo_uid = repo_uid
    self.updates = updates or {}
    self.removals = removals or []

  def perform(self):
    repo = dbi.find_one(Repo, {'uid': self.repo_uid})
    cluster_name = repo.team.cluster.name
    deploy_name = repo.deploy_name

    if not deploy_name:
      logger.error('Not updating envs for Repo(uid={}) -- No deploy_name on repo.'.format(self.repo_uid))
      return

    success = kubectl.set_envs(deployment_name=deploy_name,
                               updates=self.updates,
                               removals=self.removals,
                               context=cluster_name,
                               cluster=cluster_name)

    if not success:
      logger.error('Failed to update envs for Repo(uid={}).'.format(self.repo_uid))