from src import dbi
from src.statuses.pred_statuses import pstatus
from src.deploys import create_deploy
from src.utils import clusters
from src.deploys.build_server_deploy import BuildServerDeploy


class PostTraining(object):

  def __int__(self, prediction=None):
    self.prediction = prediction

  def perform(self):
    # Update prediction status
    dbi.update(self.prediction, {'status': pstatus.DONE_TRAINING})

    # Schedule a deploy to the build server to build the API image
    create_deploy(BuildServerDeploy, {
      'prediction_uid': self.prediction.uid,
      'build_for': clusters.API
    })