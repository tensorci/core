import os
from time import sleep
from abstract_deploy import AbstractDeploy
from src import dbi, logger
from src.utils import clusters
from src.services.prediction_services.publicize_prediction import PublicizePrediction
from src.utils.job_queue import job_queue
from src.helpers import time_since_epoch
from kubernetes import client, config


class ApiDeploy(AbstractDeploy):

  def __init__(self, deployment_uid=None):
    super(ApiDeploy, self).__init__(deployment_uid)

  def deploy(self):
    self.set_db_reliant_attrs()
    self.container_name = '{}-{}'.format(self.prediction.slug, clusters.API)
    self.image = '{}/{}:{}'.format(self.prediction.image_repo_owner, self.container_name, self.deployment.sha)
    self.deploy_name = '{}-{}'.format(self.container_name, time_since_epoch())
    self.cluster_name = self.cluster.name
    self.ports = [80]
    self.replicas = 3

    self.envs = {
      'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID'),
      'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY'),
      'AWS_REGION_NAME': os.environ.get('AWS_REGION_NAME'),
      'S3_BUCKET_NAME': self.cluster.bucket.name,
      'DATASET_DB_URL': os.environ.get('DATASET_DB_URL'),
      'DATASET_TABLE_NAME': self.prediction.dataset_table(),
      'PREDICTION': self.prediction.slug,
      'PREDICTION_UID': self.prediction.uid,
      'CLIENT_ID': self.prediction.client_id,
      'CLIENT_SECRET': self.prediction.client_secret
    }

    if self.prediction.deploy_name:
      self.update_deploy()
    else:
      super(ApiDeploy, self).deploy()

  def update_deploy(self):
    logger.info('Updating existing deploy...', queue=self.deployment_uid)

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

    api.patch_namespaced_deployment(self.prediction.deploy_name,
                                    namespace=self.namespace,
                                    body=body)

    self.on_deploy_success()

  def on_deploy_success(self):
    if not self.prediction.deploy_name:
      self.prediction = dbi.update(self.prediction, {'deploy_name': self.deploy_name})

    if self.prediction.elb:
      self.update_deployment_status(self.deployment.statuses.PREDICTING)

      logger.info('Successfully deployed {}.'.format(self.deployment.sha),
                  queue=self.deployment_uid,
                  last_entry=True)
    else:
      sleep(3)  # wait a hot sec for deployment to be absolutely registered

      # Set up ELB and CNAME record for deployment if not already there
      publicize_pred_svc = PublicizePrediction(deployment_uid=self.deployment_uid, port=443)
      job_queue.add(publicize_pred_svc.perform, meta={'deployment': self.deployment_uid})