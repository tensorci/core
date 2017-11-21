from src import dbi
from src.statuses.pred_statuses import pstatus
from src.deploys import create_deploy
from src.deploys.api_deploy import ApiDeploy


class PostApiBuilding(object):

  def __int__(self, prediction=None):
    self.prediction = prediction

  def perform(self):
    # Update prediction status
    dbi.update(self.prediction, {'status': pstatus.DONE_BUILDING_FOR_API})

    # Schedule a deploy to the api cluster
    create_deploy(ApiDeploy, {'prediction_uid': self.prediction.uid})