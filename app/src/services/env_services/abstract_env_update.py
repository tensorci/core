from src import dbi, logger
from src.models import Repo


class AbstractEnvUpdate(object):

  def __init__(self, repo_uid=None):
    self.repo_uid = repo_uid
    self.repo = None

  def set_db_reliant_attrs(self):
    self.repo = dbi.find_one(Repo, {'uid': self.repo_uid})

    if not self.repo:
      raise BaseException('Not updating env for Repo(uid={}). Repo not found.'.format(self.repo_uid))

    if not self.repo.deploy_name:
      raise BaseException('Not updating env for Repo(uid={}). Repo has no deploy_name.'.format(self.repo_uid))
