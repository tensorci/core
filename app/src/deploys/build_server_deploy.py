import os
from abstract_deploy import AbstractDeploy
from train_deploy import TrainDeploy
from api_deploy import ApiDeploy
from src.utils import image_names, clusters
from src.config import config
from src.helpers import ms_since_epoch
from kubernetes import watch
from src.utils.aws import create_s3_bucket
from src import dbi, logger
from src.utils.job_queue import job_queue
from src.services.cluster_services.create_cluster import CreateCluster


class BuildServerDeploy(AbstractDeploy):

  def __init__(self, deployment_uid=None, build_for=None, update_prediction_model=False):
    super(BuildServerDeploy, self).__init__(deployment_uid)
    self.build_for = build_for
    self.update_prediction_model = update_prediction_model

  def deploy(self):
    self.set_db_reliant_attrs()
    self.log_stream_key = self.get_log_stream_key()
    
    self.container_name = '{}-{}-{}'.format(self.build_for, clusters.BUILD_SERVER, self.repo.uid)
    self.image = '{}/{}'.format(config.IMAGE_REPO_OWNER, image_names.BUILD_SERVER)
    self.deploy_name = '{}-{}-{}-{}'.format(self.build_for, clusters.BUILD_SERVER, self.repo.uid, ms_since_epoch(as_int=True))
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
      'REPO_SLUG': self.repo.slug,
      'REPO_UID': self.repo.uid,
      'GIT_REPO': self.repo.url(),
      'IMAGE_OWNER': self.repo.image_repo_owner,
      'FOR_CLUSTER': self.build_for,
      'SHA': self.commit.sha,
      'DEPLOYMENT_UID': self.deployment_uid,
      'REDIS_URL': os.environ.get('REDIS_URL')
    }

    if self.build_for == clusters.TRAIN:
      logger.info('Building for training cluster...', stream=self.log_stream_key, section=True, building=True)
    elif self.build_for == clusters.API:
      logger.info('Building for API cluster...', stream=self.log_stream_key, section=True, building=True)

    super(BuildServerDeploy, self).deploy()
  
  def get_log_stream_key(self):
    return {
      clusters.TRAIN: self.deployment.train_deploy_log(),
      clusters.API: self.deployment.api_deploy_log()
    }.get(self.build_for)
    
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
        logger.info('Job {} started.'.format(self.deploy_name))

      if status.get('failed') is not None:
        logger.error('FAILED JOB, {}, for deployment(sha={}) of repo(slug={}).'.format(
          self.deploy_name, self.commit.sha, self.repo.slug))

        logger.error('Build job failed.', stream=self.log_stream_key, building=True)
        watcher.stop()

      if status.get('succeeded'):
        logger.info('Successfully built image.', stream=self.log_stream_key, building=True)
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

      logger.info('Configuring model storage...', stream=self.log_stream_key, section=True)

      if not bucket_success:
        logger.error('Model storage creation failed.', stream=self.log_stream_key)
        return

      logger.info('Done.', stream=self.log_stream_key)

      dbi.update(self.bucket, {'name': bucket_name})

    logger.info('Scheduling deploy to training cluster...', stream=self.log_stream_key, section=True)

    # Schedule a deploy to the training cluster
    train_deployer = TrainDeploy(deployment_uid=self.deployment_uid,
                                 update_prediction_model=self.update_prediction_model)

    job_queue.add(train_deployer.deploy, meta={'deployment': self.deployment_uid})

    self.update_deployment_status(self.deployment.statuses.TRAINING_SCHEDULED)

  def post_api_building(self):
    self.update_deployment_status(self.deployment.statuses.DONE_BUILDING_FOR_API)

    if self.cluster.validated:
      # Go ahead and deploy if cluster already created/validated
      self.create_api_deploy()
    else:
      # Create cluster before API deploy if it doesn't exist yet
      self.create_cluster_and_deploy()

  def create_api_deploy(self):
    logger.info('Scheduling deploy to API cluster...', stream=self.log_stream_key, section=True)

    api_deployer = ApiDeploy(deployment_uid=self.deployment_uid)
    job_queue.add(api_deployer.deploy, meta={'deployment': self.deployment_uid})

    self.update_deployment_status(self.deployment.statuses.PREDICTING_SCHEDULED)

  def create_cluster_and_deploy(self):
    logger.info('Scheduling API cluster creation...', stream=self.log_stream_key, section=True)

    create_cluster_svc = CreateCluster(team_uid=self.team.uid,
                                       deployment_uid=self.deployment_uid,
                                       with_deploy=True)

    job_queue.add(create_cluster_svc.perform, meta={'deployment': self.deployment_uid})