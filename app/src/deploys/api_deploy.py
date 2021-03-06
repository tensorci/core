import os
from time import sleep
from abstract_deploy import AbstractDeploy
from src import dbi, logger
from src.utils import clusters
from src.services.prediction_services.publicize_prediction import PublicizePrediction
from src.services.cluster_services.export_cluster import ExportCluster
from src.utils.job_queue import job_queue
from src.helpers import ms_since_epoch
from kubernetes import client, config
from src.helpers.deployment_helper import api_deploy_envs


class ApiDeploy(AbstractDeploy):

  def __init__(self, deployment_uid=None):
    super(ApiDeploy, self).__init__(deployment_uid)
    self.stage = None

  def deploy(self):
    self.set_db_reliant_attrs()
    self.log_stream_key = self.deployment.api_deploy_log()
    self.stage = self.deployment.statuses.PREDICTING_SCHEDULED

    self.container_name = '{}-{}'.format(clusters.API, self.repo.uid)
    self.image = '{}/{}:{}'.format(self.repo.image_repo_owner, self.container_name, self.commit.sha)
    self.deploy_name = '{}-{}-{}'.format(clusters.API, self.repo.uid, ms_since_epoch(as_int=True))
    self.cluster_name = self.cluster.name
    self.ports = [443]
    self.replicas = 3

    self.envs = api_deploy_envs(self.repo, cluster=self.cluster, dataset=self.dataset)
    self.add_custom_envs()

    # Ensure cluster/context exists in KUBECONFIG
    context_exported = ExportCluster(cluster=self.cluster).perform()

    if not context_exported:
      logger.error('Failure exporting cluster context.', stream=self.log_stream_key, stage=self.stage)
      return

    logger.info('Deploying...', stream=self.log_stream_key, section=True, stage=self.stage)

    if self.repo.deploy_name:
      self.update_deploy()
    else:
      super(ApiDeploy, self).deploy()

  def add_custom_envs(self):
    for env in self.repo.api_envs():
      if env.name not in self.envs:
        self.envs[env.name] = env.value

  def update_deploy(self):
    body = {
      'spec': {
        'template': {
          'spec': {
            'containers': [
              {
                'name': self.container_name,
                'image': self.image
              }
            ]
          }
        }
      }
    }

    api_client = config.new_client_from_config(context=self.cluster_name)

    api = client.ExtensionsV1beta1Api(api_client=api_client)

    api.patch_namespaced_deployment(self.repo.deploy_name,
                                    namespace=self.namespace,
                                    body=body)

    self.on_deploy_success()

  def on_deploy_success(self):
    if not self.repo.deploy_name:
      self.repo = dbi.update(self.repo, {'deploy_name': self.deploy_name})

    if self.repo.elb:
      self.update_deployment_status(self.deployment.statuses.PREDICTING)

      logger.info('Successfully deployed to API.', stream=self.log_stream_key, stage=self.stage)

      logger.info('Prediction live at wss://{}'.format(self.repo.domain),
                  stream=self.log_stream_key,
                  stage=self.stage,
                  last_entry=True)
    else:
      logger.info('Successfully deployed to API.', stream=self.log_stream_key, stage=self.stage)

      logger.info('Scheduling prediction for publication...', stream=self.log_stream_key, section=True, stage=self.stage)

      sleep(3)  # wait a hot sec for deployment to be absolutely registered

      # Set up ELB and CNAME record for deployment if not already there
      publicize_pred_svc = PublicizePrediction(deployment_uid=self.deployment_uid, port=443, target_port=443)
      job_queue.add(publicize_pred_svc.perform, meta={'deployment': self.deployment_uid})