import os
from abstract_deploy import AbstractDeploy
from src.utils import clusters
from src.config import get_config
from src import dbi
from src.statuses.pred_statuses import pstatus
from src.services.prediction_services.publicize_prediction import PublicizePrediction

config = get_config()


class ApiDeploy(AbstractDeploy):

  def __init__(self, prediction_uid=None):
    super(ApiDeploy, self).__init__(prediction_uid)

    self.image = '{}/{}-{}'.format(config.IMAGE_REPO_OWNER, self.prediction.slug, clusters.API)
    self.deploy_name = '{}-{}'.format(self.prediction.slug, clusters.API)
    self.cluster = self.team.cluster.name
    self.ports = [80]

    self.envs = {
      'DATASET_DB_URL': os.environ.get('DATASET_DB_URL'),
      'TEAM': self.team.slug,
      'TEAM_UID': self.team.uid,
      'PREDICTION': self.prediction.slug,
      'PREDICTION_UID': self.prediction.uid
    }

  def deploy(self):
    # Perform deploy
    super(ApiDeploy, self).deploy()

    # Update the status of the new prediction
    print('Updating Prediction({}) of Team({}) to status: {}'.format(
      self.prediction.slug, self.team.slug, self.prediction.status))

    # TODO: Secure this better and move into Prediction model as a helper function
    new_status = pstatus.next_status(self.prediction.status)
    dbi.update(self.prediction, {'status': new_status})

    # Set up ELB and CNAME record for deployment if not already done
    if not self.prediction.elb:
      PublicizePrediction(self.prediction).perform()
