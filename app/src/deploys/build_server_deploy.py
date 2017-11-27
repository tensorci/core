import os
from abstract_deploy import AbstractDeploy
from src.utils import image_names, clusters
from src.config import get_config
from src import dbi
from src.statuses.pred_statuses import pstatus
from src.helpers import time_since_epoch
from kubernetes import watch

config = get_config()


class BuildServerDeploy(AbstractDeploy):

  def __init__(self, prediction_uid=None, build_for=None):
    super(BuildServerDeploy, self).__init__(prediction_uid)

    self.build_for = build_for
    self.image = '{}/{}'.format(config.IMAGE_REPO_OWNER, image_names.BUILD_SERVER)
    self.deploy_name = '{}-{}-build-{}'.format(self.prediction.slug, self.build_for, time_since_epoch())
    self.cluster = os.environ.get('BS_CLUSTER_NAME')
    self.job = True
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
      'TEAM': self.team.slug,
      'TEAM_UID': self.team.uid,
      'PREDICTION': self.prediction.slug,
      'PREDICTION_UID': self.prediction.uid,
      'GIT_REPO': self.prediction.git_repo,
      'IMAGE_OWNER': self.prediction.image_repo_owner,
      'FOR_CLUSTER': self.build_for
    }

  def on_deploy_success(self):
    post_deploy_status = {
      clusters.TRAIN: pstatus.BUILDING_FOR_TRAIN,
      clusters.API: pstatus.BUILDING_FOR_API
    }.get(self.build_for)

    self.update_pred_status(post_deploy_status)

    self.watch_job()

  def watch_job(self):
    watcher = watch.Watch()

    label_selector = 'app={}'.format(self.deploy_name)

    for e in watcher.stream(self.api.list_namespaced_job, namespace=self.namespace, label_selector=label_selector):
      type = e.get('type')
      raw_obj = e.get('raw_object', {})
      status = raw_obj.get('status', {})

      if type == 'ADDED':
        print('Job {} started.'.format(self.deploy_name))

      if status.get('failed') is not None:
        print('FAILED JOB, {}, for prediction(uid={}).'.format(self.deploy_name, self.prediction_uid))
        watcher.stop()

      if status.get('succeeded'):
        print('Job {} succeeded.'.format(self.deploy_name))
        self.on_build_success()
        watcher.stop()

  def on_build_success(self):
    done_building_status = {
      clusters.TRAIN: pstatus.DONE_BUILDING_FOR_TRAIN,
      clusters.API: pstatus.DONE_BUILDING_FOR_API
    }.get(self.build_for)

    self.update_pred_status(done_building_status)

  def update_pred_status(self, status):
    print('Updating Prediction(slug={}) of Team(slug={}) to status: {}'.format(
      self.prediction.slug, self.team.slug, status))

    dbi.update(self.prediction, {'status': status})
