from src import dbi
from src.deploys import create_deploy
from src.utils import clusters
from src.deploys.build_server_deploy import BuildServerDeploy


class DoneTraining(object):

  def __init__(self, deployment=None):
    self.deployment = deployment

  def perform(self):
    # Update deployment status
    dbi.update(self.deployment, {'status': self.deployment.statuses.DONE_TRAINING})

    # Schedule a deploy to the build server to build the API image
    create_deploy(BuildServerDeploy, {
      'deployment_uid': self.deployment.uid,
      'build_for': clusters.API
    })