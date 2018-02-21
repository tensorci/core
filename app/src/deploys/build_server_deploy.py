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
    self.repo_access_token = self.get_repo_access_token()
    
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
      'REPO_UID': self.repo.uid,
      'REPO_SLUG': self.repo.slug,
      'TEAM_SLUG': self.team.slug,
      'PROVIDER_DOMAIN': self.provider.domain,
      'REPO_ACCESS_TOKEN': self.repo_access_token,
      'IMAGE_OWNER': self.repo.image_repo_owner,
      'FOR_CLUSTER': self.build_for,
      'SHA': self.commit.sha,
      'DEPLOYMENT_UID': self.deployment_uid,
      'REDIS_URL': os.environ.get('REDIS_URL')
    }

    if self.build_for == clusters.TRAIN:
      logger.info('Building for training cluster...', stream=self.log_stream_key, section=True, stage=self.get_stage(building=True))
    elif self.build_for == clusters.API:
      logger.info('Building for API cluster...', stream=self.log_stream_key, section=True, stage=self.get_stage(building=True))

    super(BuildServerDeploy, self).deploy()
  
  def get_log_stream_key(self):
    return {
      clusters.TRAIN: self.deployment.train_deploy_log(),
      clusters.API: self.deployment.api_deploy_log()
    }.get(self.build_for)

  def get_repo_access_token(self):
    """
    TODO: Make this more secure by getting the access_token from the provider_user actually
    triggering the build rather than just getting any random provider_user with write access
    to the repo and using his access token.
    """
    # Get all repo_provider_users for this repo, regardless of their permissions.
    repo_provider_users = self.repo.repo_provider_users or []

    # If no repo_provider_users exist, something's wrong
    if not repo_provider_users:
      logger.error('No repo_provider_users found for Repo(id={})...'.format(self.repo.id))
      return ''

    # Find the first repo_provider_user with write access
    rpu_with_write_access = None
    for rpu in repo_provider_users:
      if rpu.has_write_access():
        rpu_with_write_access = rpu
        break

    # If no one has write access just use the first repo_provide_user
    if rpu_with_write_access:
      provider_user = rpu_with_write_access.provider_user
    else:
      provider_user = repo_provider_users[0].provider_user

    # Return an access token with write permissions to this repo.
    return provider_user.access_token

  def get_stage(self, building=False):
    statuses = self.deployment.statuses

    if building:
      return {
        clusters.TRAIN: statuses.BUILDING_FOR_TRAIN,
        clusters.API: statuses.BUILDING_FOR_API
      }.get(self.build_for)
    else:
      return {
        clusters.TRAIN: statuses.TRAINING_SCHEDULED,
        clusters.API: statuses.PREDICTING_SCHEDULED
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

    for e in watcher.stream(self.api.list_namespaced_pod, namespace=self.namespace, label_selector=label_selector):
      etype = e.get('type', '').lower()
      raw_obj = e.get('raw_object', {})
      status = raw_obj.get('status', {})
      phase = status.get('phase', '').lower()

      logger.info('Status: {}\nPhase: {}\n'.format(status, phase))

      if etype == 'added':
        logger.info('Job {} started.'.format(self.deploy_name))

      if phase == 'failed':
        logger.error('FAILED JOB, {}, for deployment(sha={}) of repo(slug={}).'.format(
          self.deploy_name, self.commit.sha, self.repo.slug))

        logger.error('Build job failed.', stream=self.log_stream_key, stage=self.get_stage(building=True))
        watcher.stop()

      if phase == 'succeeded':
        logger.info('Successfully built image.', stream=self.log_stream_key, stage=self.get_stage(building=True))
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

      logger.info('Configuring model storage...', stream=self.log_stream_key, section=True, stage=self.get_stage())

      if not bucket_success:
        logger.error('Model storage creation failed.', stream=self.log_stream_key, stage=self.get_stage())
        return

      logger.info('Done.', stream=self.log_stream_key, stage=self.get_stage())

      dbi.update(self.bucket, {'name': bucket_name})

    logger.info('Scheduling deploy to training cluster...', stream=self.log_stream_key, section=True, stage=self.get_stage())

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
    logger.info('Scheduling deploy to API cluster...', stream=self.log_stream_key, section=True, stage=self.get_stage())

    api_deployer = ApiDeploy(deployment_uid=self.deployment_uid)
    job_queue.add(api_deployer.deploy, meta={'deployment': self.deployment_uid})

    self.update_deployment_status(self.deployment.statuses.PREDICTING_SCHEDULED)

  def create_cluster_and_deploy(self):
    logger.info('Scheduling API cluster creation...', stream=self.log_stream_key, section=True, stage=self.get_stage())

    create_cluster_svc = CreateCluster(team_uid=self.team.uid,
                                       deployment_uid=self.deployment_uid,
                                       with_deploy=True)

    job_queue.add(create_cluster_svc.perform, meta={'deployment': self.deployment_uid})