import os
from abstract_deploy import AbstractDeploy
from src.utils import clusters
from src.config import get_config
from src.statuses.pred_statuses import pstatus
from src.helpers import time_since_epoch

config = get_config()


class TrainDeploy(AbstractDeploy):

  def __init__(self, prediction_uid=None):
    super(TrainDeploy, self).__init__(prediction_uid)

    self.image = '{}/{}-{}'.format(config.IMAGE_REPO_OWNER, self.prediction.slug, clusters.TRAIN)
    self.deploy_name = '{}-{}-{}'.format(self.prediction.slug, clusters.TRAIN, time_since_epoch())
    self.cluster = os.environ.get('TRAIN_CLUSTER_NAME')
    self.job = True
    self.restart_policy = 'Never'

    if self.team.cluster:
      s3_bucket_name = self.team.cluster.state.replace('s3://', '')
    else:
      s3_bucket_name = '{}-{}'.format(self.team.slug, self.team.uid)

    self.envs = {
      'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID'),
      'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY'),
      'AWS_REGION_NAME': os.environ.get('AWS_REGION_NAME'),
      'S3_BUCKET_NAME': s3_bucket_name,
      'DATASET_DB_URL': os.environ.get('DATASET_DB_URL'),
      'CORE_URL': 'https://app.{}/api'.format(config.DOMAIN),
      'CORE_API_TOKEN': os.environ.get('CORE_API_TOKEN'),
      'TEAM': self.team.slug,
      'TEAM_UID': self.team.uid,
      'PREDICTION': self.prediction.slug,
      'PREDICTION_UID': self.prediction.uid
    }

  def on_deploy_success(self):
    self.update_pred_status(pstatus.TRAINING)