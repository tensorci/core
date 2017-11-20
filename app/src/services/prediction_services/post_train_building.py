from status_transition_service import StatusTransitionService
from src import dbi
from src.statuses.pred_statuses import pstatus


class PostTrainBuilding(StatusTransitionService):

  def __int__(self, prediction_uid=None):
    super(PostTrainBuilding, self).__init__(prediction_uid)

  def perform(self):
    # Update prediction status
    dbi.update(self.prediction, {'status': pstatus.DONE_BUILDING_FOR_TRAIN})

    # Schedule a deploy to the training cluster
