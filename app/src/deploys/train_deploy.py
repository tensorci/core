import os
from abstract_deploy import AbstractDeploy
from src.utils import clusters
from src.config import get_config
from src.helpers import time_since_epoch

config = get_config()


class TrainDeploy(AbstractDeploy):

  def __init__(self, deployment_uid=None):
    super(TrainDeploy, self).__init__(deployment_uid)

    self.container_name = '{}-{}'.format(self.prediction.slug, clusters.TRAIN)
    self.image = '{}/{}'.format(self.prediction.image_repo_owner, self.container_name)
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
      'TEAM': self.team.slug,
      'TEAM_UID': self.team.uid,
      'PREDICTION': self.prediction.slug,
      'PREDICTION_UID': self.prediction.uid,
      'DEPLOYMENT_UID': self.deployment_uid
    }

  def on_deploy_success(self):
    self.update_deployment_status(self.deployment.statuses.TRAINING)