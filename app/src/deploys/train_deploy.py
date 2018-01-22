import os
from abstract_deploy import AbstractDeploy
from src import logger, dbi
from src.models import TrainJob
from src.utils import clusters
from src.config import config
from src.helpers import ms_since_epoch


class TrainDeploy(AbstractDeploy):

  def __init__(self, deployment_uid=None, update_prediction_model=False):
    super(TrainDeploy, self).__init__(deployment_uid)
    self.update_prediction_model = update_prediction_model
    self.stage = None

  def deploy(self):
    self.set_db_reliant_attrs()
    self.log_stream_key = self.deployment.train_deploy_log()
    self.stage = self.deployment.statuses.TRAINING_SCHEDULED

    self.container_name = '{}-{}'.format(clusters.TRAIN, self.repo.uid)
    self.image = '{}/{}:{}'.format(self.repo.image_repo_owner, self.container_name, self.commit.sha)
    self.deploy_name = '{}-{}-{}'.format(clusters.TRAIN, self.repo.uid, ms_since_epoch(as_int=True))
    self.cluster = self.team.cluster
    self.cluster_name = os.environ.get('TRAIN_CLUSTER_NAME')
    self.job = True
    self.restart_policy = 'Never'

    if self.dataset:
      dataset_table = self.dataset.table()
    else:
      dataset_table = ''

    self.envs = {
      'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID'),
      'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY'),
      'AWS_REGION_NAME': os.environ.get('AWS_REGION_NAME'),
      'S3_BUCKET_NAME': self.cluster.bucket.name,
      'DATASET_DB_URL': os.environ.get('DATASET_DB_URL'),
      'DATASET_TABLE_NAME': dataset_table,
      'CORE_URL': config.CORE_URL,
      'CORE_API_TOKEN': os.environ.get('CORE_API_TOKEN'),
      'REPO_SLUG': self.repo.slug,
      'REPO_UID': self.repo.uid,
      'DEPLOYMENT_UID': self.deployment_uid,
      'REDIS_URL': os.environ.get('REDIS_URL'),
      'UPDATE_PREDICTION_MODEL': str(self.update_prediction_model).lower()
    }

    # Add user-defined environment variables
    self.add_custom_envs()

    logger.info('Deploying...', stream=self.log_stream_key, section=True, stage=self.stage)

    super(TrainDeploy, self).deploy()

  def add_custom_envs(self):
    for env in self.repo.envs:
      if env.name not in self.envs:
        self.envs[env.name] = env.value

  def on_deploy_success(self):
    # Update deployment status to TRAINING
    self.update_deployment_status(self.deployment.statuses.TRAINING)

    # Create a TrainJob for this Deployment to track time spent on cluster
    dbi.create(TrainJob, {'deployment': self.deployment})

    logger.info('Successfully deployed to training cluster.', stream=self.log_stream_key, last_entry=True, stage=self.stage)