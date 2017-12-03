import os
from time import sleep
from abstract_deploy import AbstractDeploy
from src import dbi
from src.utils import clusters
from src.config import get_config
from src.statuses.pred_statuses import pstatus
from src.services.prediction_services.publicize_prediction import PublicizePrediction
from src.helpers import time_since_epoch
from src import delayed
from src.helpers.delay_helper import delay_class_method

config = get_config()


class ApiDeploy(AbstractDeploy):

  def __init__(self, prediction_uid=None):
    super(ApiDeploy, self).__init__(prediction_uid)

    self.container_name = '{}-{}'.format(self.prediction.slug, clusters.API)
    self.image = '{}/{}'.format(config.IMAGE_REPO_OWNER, self.container_name)
    self.deploy_name = '{}-{}'.format(self.container_name, time_since_epoch())
    self.cluster = self.team.cluster
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
      'TEAM': self.team.slug,
      'TEAM_UID': self.team.uid,
      'PREDICTION': self.prediction.slug,
      'PREDICTION_UID': self.prediction.uid
    }

  # def deploy(self):
  #   if self.prediction.deploy_name:
  #     os.system('kubectl set image deployment/{} {}={} --context={} --cluster={}'.format(
  #       self.prediction.deploy_name, self.container_name, self.image, self.cluster_name, self.cluster_name))
  #   else:
  #     # envs = []
  #     # for k, v in self.envs.items():
  #     #   envs.append('--env="{}={}"'.format(k, v))
  #     #
  #     # os.system('kubectl run {} --image={} --port={} {}'.format(self.deploy_name, self.image, 80, ' '.join(envs)))
  #
  #   self.update_pred_status(pstatus.PREDICTING)

  def on_deploy_success(self):
    if not self.prediction.deploy_name:
      self.prediction = dbi.update(self.prediction, {'deploy_name': self.deploy_name})

    self.update_pred_status(pstatus.PREDICTING)

    # Set up ELB and CNAME record for deployment if not already there
    if not self.prediction.elb:
      sleep(5)

      delayed.add_job(delay_class_method, args=[PublicizePrediction, {
        'prediction_uid': self.prediction.uid
      }])
