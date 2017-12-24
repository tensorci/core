from src import dbi, logger
from src.models import Prediction
from abstract_api import AbstractApi, ApiException


class PredMessenger(object):
  header_name = 'TensorCI-Internal-Msg-Token'

  def __init__(self, prediction_uid=None):
    self.prediction_uid = prediction_uid
    self.prediction = None

  def update_model(self):
    self.set_db_reliant_attrs()
    api = self.configure_api()

    try:
      api.put('/model')
    except ApiException as e:
      logger.error('Message to update model failed for prediction, {}, with code({}), status({}), error({})'.format(
        self.prediction.slug, e.code, e.status, e.error))

  def configure_api(self):
    return AbstractApi(base_url=self.prediction.api_url(),
                       auth_header_name=self.header_name,
                       auth_header_value=self.prediction.internal_msg_token)

  def set_db_reliant_attrs(self):
    self.prediction = dbi.find_one(Prediction, {'uid': self.prediction_uid})
