from abstract_env_update import AbstractEnvUpdate


class RemoveDeployEnv(AbstractEnvUpdate):

  def __init__(self, repo_uid=None, env_name=None):
    super(AbstractEnvUpdate, self).__init__(repo_uid)
    self.env_name = env_name

  def perform(self):
    self.set_db_reliant_attrs()

    # Remove env_name