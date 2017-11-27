import os
from abstract_deploy import AbstractDeploy
from train_deploy import TrainDeploy
from src import dbi
from api_deploy import ApiDeploy
from src.utils import image_names, clusters
from src.config import get_config
from src.statuses.pred_statuses import pstatus
from src.helpers import time_since_epoch
from kubernetes import watch
from src.deploys import create_deploy
from src.utils.aws import create_s3_bucket
from src.scheduler import delayed, delay_class_method
from src.services.cluster_services.create_cluster import CreateCluster

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
      'PREDICTION_UID': self.prediction_uid,
      'GIT_REPO': self.prediction.git_repo,
      'IMAGE_OWNER': self.prediction.image_repo_owner,
      'FOR_CLUSTER': self.build_for,
      'SHA': self.prediction.sha
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
    post_building_action = {
      clusters.TRAIN: self.post_train_building,
      clusters.API: self.post_api_building
    }.get(self.build_for)

    post_building_action()

  def post_train_building(self):
    self.update_pred_status(pstatus.DONE_BUILDING_FOR_TRAIN)

    bucket = self.team.cluster.bucket

    if not bucket.name:
      print('Creating S3 bucket for Team(slug={})...'.format(self.team.slug))

      bucket_name = '{}-{}'.format(self.team.slug, self.team.uid)
      bucket_creation_success = create_s3_bucket(bucket_name)

      if not bucket_creation_success:
        print('Bucket creation failed. Returning from post_train_building.')
        return

      dbi.update(bucket, {'name': bucket_name})

    # Schedule a deploy to the training cluster
    print('Scheduling training deploy for prediction(slug={})...'.format(self.prediction.slug))
    create_deploy(TrainDeploy, {'prediction_uid': self.prediction_uid})

  def post_api_building(self):
    self.update_pred_status(pstatus.DONE_BUILDING_FOR_API)

    # If team's cluster already exists, go ahead and deploy to it.
    if self.team.cluster:
      print('Scheduling api deploy for prediction(slug={})...'.format(self.prediction.slug))
      create_deploy(ApiDeploy, {'prediction_uid': self.prediction_uid})
    else:
      # Otherwise, create the cluster first, then deploy (all as delayed job).
      print('Scheduling cluster creation for prediction(slug={})...'.format(self.prediction.slug))

      delayed.add_job(delay_class_method, args=[CreateCluster, {
        'team_uid': self.team.uid,
        'prediction_uid': self.prediction_uid,
        'with_deploy': True
      }])