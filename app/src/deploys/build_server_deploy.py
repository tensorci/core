import os
from abstract_deploy import AbstractDeploy
from train_deploy import TrainDeploy
from api_deploy import ApiDeploy
from src.utils import image_names, clusters
from src.config import get_config
from src.helpers import time_since_epoch
from kubernetes import watch
from src.utils.aws import create_s3_bucket
from src import dbi
from src.utils.queue import job_queue
from src.services.cluster_services.create_cluster import CreateCluster

config = get_config()


class BuildServerDeploy(AbstractDeploy):

  def __init__(self, deployment_uid=None, build_for=None):
    super(BuildServerDeploy, self).__init__(deployment_uid)
    self.build_for = build_for

  def deploy(self):
    self.set_db_reliant_attrs()

    self.container_name = '{}-{}-build'.format(self.prediction.slug, self.build_for)
    self.image = '{}/{}'.format(config.IMAGE_REPO_OWNER, image_names.BUILD_SERVER)
    self.deploy_name = '{}-{}'.format(self.container_name, time_since_epoch())
    self.cluster_name = os.environ.get('BS_CLUSTER_NAME')
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
      'FOR_CLUSTER': self.build_for,
      'SHA': self.deployment.sha
    }

    super(BuildServerDeploy, self).deploy()

  def on_deploy_success(self):
    post_deploy_status = {
      clusters.TRAIN: self.deployment.statuses.BUILDING_FOR_TRAIN,
      clusters.API: self.deployment.statuses.BUILDING_FOR_API
    }.get(self.build_for)

    self.update_deployment_status(post_deploy_status)

    self.watch_job()

  def watch_job(self):
    watcher = watch.Watch()

    label_selector = 'app={}'.format(self.deploy_name)

    for e in watcher.stream(self.api.list_namespaced_job, namespace=self.namespace, label_selector=label_selector):
      etype = e.get('type')
      raw_obj = e.get('raw_object', {})
      status = raw_obj.get('status', {})

      if etype == 'ADDED':
        self.log('Job {} started.'.format(self.deploy_name))

      if status.get('failed') is not None:
        self.log('FAILED JOB, {}, for deployment(sha={}) of prediction(slug={}).'.format(
          self.deploy_name, self.deployment.sha, self.prediction.slug))
        watcher.stop()

      if status.get('succeeded'):
        self.log('Job {} succeeded.'.format(self.deploy_name))
        self.on_build_success()
        watcher.stop()

  def on_build_success(self):
    post_building_action = {
      clusters.TRAIN: self.post_train_building,
      clusters.API: self.post_api_building
    }.get(self.build_for)

    post_building_action()

  def post_train_building(self):
    self.update_deployment_status(self.deployment.statuses.DONE_BUILDING_FOR_TRAIN)

    # Create S3 Bucket for team if not there yet
    if not self.bucket.name:
      bucket_name = '{}-{}'.format(self.team.slug, self.team.uid)
      bucket_success = create_s3_bucket(bucket_name)

      if not bucket_success:
        self.log('Bucket creation failed. Returning from post_train_building.')
        return

      dbi.update(self.bucket, {'name': bucket_name})

    self.log('Scheduling training deploy for prediction(slug={})...'.format(self.prediction.slug))

    # Schedule a deploy to the training cluster
    train_deployer = TrainDeploy(deployment_uid=self.deployment_uid)

    job_queue.enqueue(train_deployer.deploy, timeout=1800)

  def post_api_building(self):
    self.update_deployment_status(self.deployment.statuses.DONE_BUILDING_FOR_API)

    if self.cluster.validated:
      # Go ahead and deploy if cluster already created/validated
      self.create_api_deploy()
    else:
      # Create cluster before API deploy if it doesn't exist yet
      self.create_cluster_and_deploy()

  def create_api_deploy(self):
    self.log('Scheduling api deploy for prediction(slug={})...'.format(self.prediction.slug))

    api_deployer = ApiDeploy(deployment_uid=self.deployment_uid)

    job_queue.enqueue(api_deployer.deploy, timeout=1800)

  def create_cluster_and_deploy(self):
    self.log('Scheduling cluster creation for team(slug={})...'.format(self.team.slug))

    create_cluster_svc = CreateCluster(team_uid=self.team.uid,
                                       deployment_uid=self.deployment_uid,
                                       with_deploy=True)

    job_queue.enqueue(create_cluster_svc.perform, timeout=1800)