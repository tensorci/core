import os
from abstract_deploy import AbstractDeploy
from src.utils import image_names, clusters
from src.config import get_config
from src import dbi
from src.statuses.pred_statuses import pstatus

config = get_config()


class BuildServerDeploy(AbstractDeploy):

  def __init__(self, prediction_uid=None, build_for=None):
    super(BuildServerDeploy, self).__init__(prediction_uid)

    self.build_for = build_for
    self.image = '{}/{}'.format(config.IMAGE_REPO_OWNER, image_names.BUILD_SERVER)
    self.deploy_name = '{}-{}-build'.format(self.prediction.slug, self.build_for)
    self.cluster = os.environ.get('BS_CLUSTER_NAME')

    self.envs = {
      'DOCKER_USERNAME': os.environ.get('DOCKER_USERNAME'),
      'DOCKER_PASSWORD': os.environ.get('DOCKER_PASSWORD'),
      'CORE_URL': 'https://{}/api'.format(config.DOMAIN),
      'CORE_API_TOKEN': os.environ.get('CORE_API_TOKEN'),
      'TEAM': self.team.slug,
      'TEAM_UID': self.team.uid,
      'PREDICTION': self.prediction.slug,
      'PREDICTION_UID': self.prediction.uid,
      'GIT_REPO': self.prediction.git_repo,
      'IMAGE_OWNER': self.prediction.image_repo_owner,
      'FOR_CLUSTER': self.build_for
    }

  def deploy(self):
    # Perform deploy
    super(BuildServerDeploy, self).deploy()

    # Update the status of the prediction
    # TODO: Secure this better and move into Prediction model as a helper function
    new_status = pstatus.next_status(self.prediction.status)

    print('Updating Prediction({}) of Team({}) to status: {}'.format(
      self.prediction.slug, self.team.slug, new_status))

    dbi.update(self.prediction, {'status': new_status})