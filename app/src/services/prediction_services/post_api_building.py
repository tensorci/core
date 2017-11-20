from status_transition_service import StatusTransitionService


class PostApiBuilding(StatusTransitionService):

  def __int__(self, prediction_uid=None):
    super(PostApiBuilding, self).__init__(prediction_uid)