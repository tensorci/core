from abstract_deploy import AbstractDeploy
from src import dbi, logger
from src.helpers import ms_since_epoch
from src.helpers.deployment_helper import api_deploy_envs
from src.services.cluster_services.export_cluster import ExportCluster
from src.utils import clusters


class ApiWorkerDeploy(AbstractDeploy):

  def __init__(self, deployment_uid=None):
    super(ApiWorkerDeploy, self).__init__(deployment_uid)
    self.stage = None

  def deploy(self):
    self.set_db_reliant_attrs()

    self.log_stream_key = self.deployment.api_deploy_log()
    self.stage = self.deployment.statuses.PREDICTING_SCHEDULED

    self.container_name = '{}-{}'.format(clusters.API, self.repo.uid)
    self.image = '{}/{}:{}'.format(self.repo.image_repo_owner, self.container_name, self.commit.sha)
    self.deploy_name = '{}-{}-{}'.format(clusters.API, self.repo.uid, ms_since_epoch(as_int=True))
    self.cluster_name = self.cluster.name
    self.ports = [80]
    self.replicas = 3

    self.envs = api_deploy_envs(self.repo, cluster=self.cluster, dataset=self.dataset)
    self.add_custom_envs()

    # Ensure cluster/context exists in KUBECONFIG
    context_exported = ExportCluster(cluster=self.cluster).perform()

    if not context_exported:
      logger.error('Failure exporting cluster context.', stream=self.log_stream_key, stage=self.stage)
      return

    super(ApiWorkerDeploy, self).deploy()

  def add_custom_envs(self):
    for env in self.repo.api_envs():
      if env.name not in self.envs:
        self.envs[env.name] = env.value

  def on_deploy_success(self):
    self.repo = dbi.update(self.repo, {'deploy_name': self.deploy_name})
    self.update_deployment_status(self.deployment.statuses.PREDICTING)
    logger.info('Successfully deployed to API.', stream=self.log_stream_key, stage=self.stage)
    logger.info('Prediction live', stream=self.log_stream_key, stage=self.stage, last_entry=True)