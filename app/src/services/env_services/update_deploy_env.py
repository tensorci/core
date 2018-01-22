from abstract_env_update import AbstractEnvUpdate


class UpdateDeployEnv(AbstractEnvUpdate):

  def __init__(self, repo_uid=None):
    super(AbstractEnvUpdate, self).__init__(repo_uid)

  def perform(self):
    self.set_db_reliant_attrs()

    # Update envs