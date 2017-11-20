import os
from abstract_deploy import AbstractDeploy
from src.utils import clusters
from src.config import get_config
from src import dbi
from src.statuses.pred_statuses import pstatus

config = get_config()


class TrainDeploy(AbstractDeploy):

  def __init__(self, prediction_uid=None):
    super(TrainDeploy, self).__init__(prediction_uid)

    self.image = '{}/{}-{}'.format(config.IMAGE_REPO_OWNER, self.prediction.slug, clusters.TRAIN)
    self.name = '{}-{}'.format(self.prediction.slug, clusters.TRAIN)
    self.cluster = clusters.TRAIN

    self.envs = {
      'DATASET_DB_URL': os.environ.get('DATASET_DB_URL'),
      'CORE_URL': 'https://{}/api'.format(config.DOMAIN),
      'CORE_API_TOKEN': os.environ.get('CORE_API_TOKEN'),
      'TEAM': self.team.slug,
      'TEAM_UID': self.team.uid,
      'PREDICTION': self.prediction.slug,
      'PREDICTION_UID': self.prediction.uid
    }

  def deploy(self):
    # Make the deploy
    super(TrainDeploy, self).deploy()

    # Update the status of the new prediction
    print('Updating Prediction({}) of Team({}) to status: {}'.format(
      self.prediction.slug, self.team.slug, self.prediction.status))

    # TODO: Secure this better and move into Prediction model as a helper function
    new_status = pstatus.next_status(self.prediction.status)
    dbi.update(self.prediction, {'status': new_status})