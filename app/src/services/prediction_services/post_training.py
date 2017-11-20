from status_transition_service import StatusTransitionService


class PostTraining(StatusTransitionService):
  
  def __int__(self, prediction_uid=None):
    super(PostTraining, self).__init__(prediction_uid)