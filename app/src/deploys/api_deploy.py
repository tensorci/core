from abstract_deploy import AbstractDeploy
from src import dbi, logger
from src.services.cluster_services.export_cluster import ExportCluster
from src.services.prediction_services.publicize_prediction import PublicizePrediction
from src.utils.job_queue import job_queue
from time import sleep


class ApiDeploy(AbstractDeploy):
  """
  Deploys the API Socket Server to a team's K8S cluster
  """

  def __init__(self, deployment_uid=None):
    super(ApiDeploy, self).__init__(deployment_uid)
    self.stage = None

  def deploy(self):
    self.set_db_reliant_attrs()

    self.log_stream_key = self.deployment.api_deploy_log()
    self.stage = self.deployment.statuses.PREDICTING_SCHEDULED

    self.container_name = self.image = self.deploy_name = 'redis'
    self.socket_port = 6379
    self.cluster_name = self.cluster.name
    self.ports = [self.socket_port]

    self.envs = {
      'TCI_USERNAME': self.repo.client_id,
      'TCI_PASSWORD': self.repo.client_secret
    }

    # Ensure cluster/context exists in KUBECONFIG
    context_exported = ExportCluster(cluster=self.cluster).perform()

    if not context_exported:
      logger.error('Failure exporting cluster context.', stream=self.log_stream_key, stage=self.stage)
      return

    logger.info('Deploying...', stream=self.log_stream_key, section=True, stage=self.stage)

    super(ApiDeploy, self).deploy()

  def on_deploy_success(self):
    logger.info('Scheduling prediction for publication...', stream=self.log_stream_key, section=True, stage=self.stage)

    sleep(3)  # wait a hot sec for deployment to be absolutely registered

    # Set up ELB and CNAME record for deployment
    publicize_pred_svc = PublicizePrediction(deployment_uid=self.deployment_uid,
                                             port=self.socket_port,
                                             target_port=self.socket_port,
                                             deploy_name=self.deploy_name,
                                             service_name=self.deploy_name,
                                             with_deploy=True)

    job_queue.add(publicize_pred_svc.perform, meta={'deployment': self.deployment_uid})