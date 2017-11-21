from src import dbi
from src.statuses.pred_statuses import pstatus
from src.deploys import create_deploy
from src.deploys.train_deploy import TrainDeploy


class PostTrainBuilding(object):

  def __int__(self, prediction=None):
    self.prediction = prediction

  def perform(self):
    # Update prediction status
    dbi.update(self.prediction, {'status': pstatus.DONE_BUILDING_FOR_TRAIN})

    # Schedule a deploy to the training cluster
    create_deploy(TrainDeploy, {'prediction_uid': self.prediction.uid})