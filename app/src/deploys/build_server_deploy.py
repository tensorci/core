import os
from abstract_deploy import AbstractDeploy
from src.utils import image_names, clusters
from src.config import get_config
from src import dbi
from src.statuses.pred_statuses import pstatus
from src.helpers import time_since_epoch

config = get_config()


class BuildServerDeploy(AbstractDeploy):

  def __init__(self, prediction_uid=None, build_for=None):
    super(BuildServerDeploy, self).__init__(prediction_uid)

    self.build_for = build_for
    self.image = '{}/{}'.format(config.IMAGE_REPO_OWNER, image_names.BUILD_SERVER)
    self.deploy_name = '{}-{}-build-{}'.format(self.prediction.slug, self.build_for, time_since_epoch())
    self.cluster = os.environ.get('BS_CLUSTER_NAME')
    self.job = True
    self.watch_job = True
    self.restart_policy = 'Never'

    # Configure volumes/mounts to allow for /var/run/docker.sock (docker daemon) to be bound to
    self.volumes = [{
      'name': 'dockersock',
      'type': 'host_path',
      'path': '/var/run'
    }]

    self.volume_mounts = [{
      'name': 'dockersock',
      'mount_path': '/var/run'
    }]

    self.envs = {
      'DOCKER_USERNAME': os.environ.get('DOCKER_USERNAME'),
      'DOCKER_PASSWORD': os.environ.get('DOCKER_PASSWORD'),
      'CORE_URL': 'https://app.{}/api'.format(config.DOMAIN),
      'CORE_API_TOKEN': os.environ.get('CORE_API_TOKEN'),
      'TEAM': self.team.slug,
      'TEAM_UID': self.team.uid,
      'PREDICTION': self.prediction.slug,
      'PREDICTION_UID': self.prediction.uid,
      'GIT_REPO': self.prediction.git_repo,
      'IMAGE_OWNER': self.prediction.image_repo_owner,
      'FOR_CLUSTER': self.build_for
    }

  def on_success(self):
    new_status = {
      clusters.TRAIN: pstatus.BUILDING_FOR_TRAIN,
      clusters.API: pstatus.BUILDING_FOR_API
    }.get(self.build_for)

    print('Updating Prediction(slug={}) of Team(slug={}) to status: {}'.format(
      self.prediction.slug, self.team.slug, new_status))

    dbi.update(self.prediction, {'status': new_status})
