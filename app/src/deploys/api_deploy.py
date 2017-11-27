import os
from abstract_deploy import AbstractDeploy
from src import dbi
from src.utils import clusters
from src.config import get_config
from src.statuses.pred_statuses import pstatus
from src.services.prediction_services.publicize_prediction import PublicizePrediction
from src.helpers import time_since_epoch

config = get_config()


class ApiDeploy(AbstractDeploy):

  def __init__(self, prediction_uid=None):
    super(ApiDeploy, self).__init__(prediction_uid)

    self.image = '{}/{}-{}'.format(config.IMAGE_REPO_OWNER, self.prediction.slug, clusters.API)
    self.deploy_name = '{}-{}-{}'.format(self.prediction.slug, clusters.API, time_since_epoch())
    self.cluster = self.team.cluster.name
    self.ports = [80]
    self.replicas = 3

    self.envs = {
      'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID'),
      'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY'),
      'AWS_REGION_NAME': os.environ.get('AWS_REGION_NAME'),
      'S3_BUCKET_NAME': self.cluster.bucket.name,
      'DATASET_DB_URL': os.environ.get('DATASET_DB_URL'),
      'TEAM': self.team.slug,
      'TEAM_UID': self.team.uid,
      'PREDICTION': self.prediction.slug,
      'PREDICTION_UID': self.prediction.uid
    }

  def on_deploy_success(self):
    # Update the prediction's deploy name
    self.prediction = dbi.update(self.prediction, {'deploy_name': self.deploy_name})

    self.update_pred_status(pstatus.PREDICTING)

    # Set up ELB and CNAME record for deployment if not already there
    if not self.prediction.elb:
      publicize_service = PublicizePrediction(prediction=self.prediction)
      publicize_service.perform()
