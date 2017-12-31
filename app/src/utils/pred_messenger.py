from src import dbi, logger
from src.models import Repo
from abstract_api import AbstractApi, ApiException


class PredMessenger(object):
  header_name = 'TensorCI-Internal-Msg-Token'

  def __init__(self, repo_uid=None):
    self.repo_uid = repo_uid
    self.repo = None

  def update_model(self):
    self.set_db_reliant_attrs()

    api = self.configure_api()

    try:
      api.put('/model')
    except ApiException as e:
      logger.error('Message to update model failed for repo(uid={}) with code({}), status({}), error({})'.format(
        self.repo.uid, e.code, e.status, e.error))

  def configure_api(self):
    return AbstractApi(base_url=self.repo.api_url(),
                       auth_header_name=self.header_name,
                       auth_header_value=self.repo.internal_msg_token)

  def set_db_reliant_attrs(self):
    self.repo = dbi.find_one(Repo, {'uid': self.repo_uid})
