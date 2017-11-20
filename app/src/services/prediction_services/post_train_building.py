from status_transition_service import StatusTransitionService


class PostTrainBuilding(StatusTransitionService):

  def __int__(self, prediction_uid=None):
    super(PostTrainBuilding, self).__init__(prediction_uid)