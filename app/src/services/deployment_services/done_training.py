from src import dbi
from src.utils import clusters
from src.deploys.build_server_deploy import BuildServerDeploy
from src.utils.queue import job_queue


class DoneTraining(object):

  def __init__(self, deployment=None):
    self.deployment = deployment

  def perform(self):
    # Update deployment status
    dbi.update(self.deployment, {'status': self.deployment.statuses.DONE_TRAINING})

    # Schedule a deploy to the build server to build the API image
    bs_deployer = BuildServerDeploy(deployment_uid=self.deployment.uid,
                                    build_for=clusters.API)

    job_queue.enqueue(bs_deployer.deploy, timeout=1800)