import os
from abstract_deploy import AbstractDeploy
from src.utils import clusters
from src.config import get_config
from src import dbi
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

    self.envs = {
      'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID'),
      'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY'),
      'AWS_REGION_NAME': os.environ.get('AWS_REGION_NAME'),
      'DATASET_DB_URL': os.environ.get('DATASET_DB_URL'),
      'CORE_URL': 'https://app.{}/api'.format(config.DOMAIN),
      'CORE_API_TOKEN': os.environ.get('CORE_API_TOKEN'),
      'TEAM': self.team.slug,
      'TEAM_UID': self.team.uid,
      'PREDICTION': self.prediction.slug,
      'PREDICTION_UID': self.prediction.uid
    }

  def on_deploy_success(self):
    new_status = pstatus.TRAINING

    print('Updating Prediction(slug={}) of Team(slug={}) to status: {}'.format(
      self.prediction.slug, self.team.slug, new_status))

    dbi.update(self.prediction, {'status': new_status})