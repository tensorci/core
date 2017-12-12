import os
from abstract_deploy import AbstractDeploy
from src.utils import clusters
from src.config import get_config
from src.helpers import time_since_epoch

config = get_config()


class TrainDeploy(AbstractDeploy):

  def __init__(self, deployment_uid=None, with_api_deploy=False):
    super(TrainDeploy, self).__init__(deployment_uid)
    self.with_api_deploy = with_api_deploy

  def deploy(self):
    self.set_db_reliant_attrs()  # TODO: turn into decorator

    self.container_name = '{}-{}'.format(self.prediction.slug, clusters.TRAIN)
    self.image = '{}/{}:{}'.format(self.prediction.image_repo_owner, self.container_name, self.deployment.sha)
    self.deploy_name = '{}-{}'.format(self.container_name, time_since_epoch())
    self.cluster = self.team.cluster
    self.cluster_name = os.environ.get('TRAIN_CLUSTER_NAME')
    self.job = True
    self.restart_policy = 'Never'

    self.envs = {
      'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID'),
      'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY'),
      'AWS_REGION_NAME': os.environ.get('AWS_REGION_NAME'),
      'S3_BUCKET_NAME': self.cluster.bucket.name,
      'DATASET_DB_URL': os.environ.get('DATASET_DB_URL'),
      'DATASET_TABLE_NAME': self.prediction.dataset_table(),
      'CORE_URL': config.CORE_URL,
      'CORE_API_TOKEN': os.environ.get('CORE_API_TOKEN'),
      'PREDICTION': self.prediction.slug,
      'PREDICTION_UID': self.prediction.uid,
      'DEPLOYMENT_UID': self.deployment_uid,
      'REDIS_URL': os.environ.get('REDIS_URL'),
      'WITH_API_DEPLOY': str(self.with_api_deploy).lower()
    }

    super(TrainDeploy, self).deploy()

  def on_deploy_success(self):
    self.update_deployment_status(self.deployment.statuses.TRAINING)
    self.log('Train deploy successful.', complete=(not self.with_api_deploy))