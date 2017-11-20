from src import dbi
from src.models import Prediction


class StatusTransitionService(object):

  def __init__(self, prediction_uid=None):
    self.prediction_uid = prediction_uid
    self.prediction = dbi.find_one(Prediction, {'uid': prediction_uid})