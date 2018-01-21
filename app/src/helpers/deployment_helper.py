from src.utils import log_formatter
from src.utils.pyredis import redis
from src.models import Deployment


def format_stages(deployment):
  statuses = deployment.statuses

  return {
    statuses.BUILDING_FOR_TRAIN: format_train_building_stage(deployment),
    statuses.TRAINING_SCHEDULED: format_train_deploying_stage(deployment),
    statuses.TRAINING: format_training_stage(deployment),
    statuses.DONE_TRAINING: format_trained_stage(deployment),
    statuses.BUILDING_FOR_API: format_api_building_stage(deployment),
    statuses.PREDICTING_SCHEDULED: format_api_deploying_stage(deployment),
    statuses.PREDICTING: format_predicting_stage(deployment)
  }


def format_train_building_stage(deployment):
  stage = deployment.statuses.BUILDING_FOR_TRAIN

  return {
    'name': 'Building for training cluster',
    'show': True,
    'succeeded': stage_succeeded(deployment, stage),
    'failed': stage_failed(deployment, stage),
    'logs': [log_formatter.deploy_log(data).rstrip()
             for ts, data in redis.xrange(deployment.train_deploy_log())
             if data.get('building') == 'True']
  }


def format_train_deploying_stage(deployment):
  stage = deployment.statuses.TRAINING_SCHEDULED

  content = {
    'name': 'Deploying to training cluster',
    'show': False,
    'succeeded': stage_succeeded(deployment, stage),
    'failed': stage_failed(deployment, stage),
    'logs': []
  }

  if should_show_stage(deployment, stage):
    content['show'] = True
    content['logs'] = [log_formatter.deploy_log(data).rstrip()
                       for ts, data in redis.xrange(deployment.train_deploy_log())
                       if data.get('building') != 'True']

  return content


def format_training_stage(deployment):
  stage = deployment.statuses.TRAINING

  content = {
    'name': 'Training',
    'show': False,
    'succeeded': stage_succeeded(deployment, stage),
    'failed': stage_failed(deployment, stage),
    'logs': []
  }

  if should_show_stage(deployment, stage):
    content['show'] = True
    content['logs'] = [log_formatter.training_log(data, with_ts=False).rstrip()
                       for ts, data in redis.xrange(deployment.train_log())]

  return content


def format_trained_stage(deployment):
  return {
    'name': 'Trained',
    'show': deployment.status_greater_than(deployment.statuses.TRAINING)
  }


def format_api_building_stage(deployment):
  stage = deployment.statuses.BUILDING_FOR_API

  content = {
    'name': 'Building for API',
    'show': False,
    'succeeded': stage_succeeded(deployment, stage),
    'failed': stage_failed(deployment, stage),
    'logs': []
  }

  if should_show_stage(deployment, stage):
    content['show'] = True
    content['logs'] = [log_formatter.deploy_log(data).rstrip()
                       for ts, data in redis.xrange(deployment.api_deploy_log())
                       if data.get('building') == 'True']

  return content


def format_api_deploying_stage(deployment):
  stage = deployment.statuses.PREDICTING_SCHEDULED

  content = {
    'name': 'Deploying to API',
    'show': False,
    'succeeded': stage_succeeded(deployment, stage),
    'failed': stage_failed(deployment, stage),
    'logs': []
  }

  if should_show_stage(deployment, stage):
    content['show'] = True
    content['logs'] = [log_formatter.deploy_log(data).rstrip()
                       for ts, data in redis.xrange(deployment.api_deploy_log())
                       if data.get('building') != 'True']
  return content


def format_predicting_stage(deployment):
  return {
    'name': 'Predicting',
    'show': deployment.status == deployment.statuses.PREDICTING
  }


def current_stage(deployment):
  statuses = deployment.statuses

  return {
    # Building for training cluster
    statuses.CREATED: statuses.BUILDING_FOR_TRAIN,
    statuses.TRAIN_BUILD_SCHEDULED: statuses.BUILDING_FOR_TRAIN,
    statuses.BUILDING_FOR_TRAIN: statuses.BUILDING_FOR_TRAIN,

    # Deploying to training cluster
    statuses.DONE_BUILDING_FOR_TRAIN: statuses.TRAINING_SCHEDULED,
    statuses.TRAINING_SCHEDULED: statuses.TRAINING_SCHEDULED,

    # Training
    statuses.TRAINING: statuses.TRAINING,

    # Trained
    statuses.DONE_TRAINING: statuses.DONE_TRAINING,

    # Building for API
    statuses.API_BUILD_SCHEDULED: statuses.BUILDING_FOR_API,
    statuses.BUILDING_FOR_API: statuses.BUILDING_FOR_API,

    # Deploying to API
    statuses.DONE_BUILDING_FOR_API: statuses.PREDICTING_SCHEDULED,
    statuses.PREDICTING_SCHEDULED: statuses.PREDICTING_SCHEDULED,

    # Predicting
    statuses.PREDICTING: statuses.PREDICTING
  }.get(deployment.status)


def ordered_stages():
  statuses = Deployment.statuses

  return [
    statuses.BUILDING_FOR_TRAIN,
    statuses.TRAINING_SCHEDULED,
    statuses.TRAINING,
    statuses.DONE_TRAINING,
    statuses.BUILDING_FOR_API,
    statuses.PREDICTING_SCHEDULED,
    statuses.PREDICTING,
  ]


def should_show_stage(deployment, stage):
  stages = ordered_stages()
  return stages.index(current_stage(deployment)) >= stages.index(stage)


def stage_succeeded(deployment, stage):
  stages = ordered_stages()
  return stages.index(current_stage(deployment)) > stages.index(stage)


def stage_failed(deployment, stage):
  return deployment.failed and current_stage(deployment) == stage


def log_info_for_deployment(deployment):
  statuses = deployment.statuses
  curr_stage = current_stage(deployment)

  log_stream_key = {
    statuses.BUILDING_FOR_TRAIN: deployment.train_deploy_log(),
    statuses.TRAINING_SCHEDULED: deployment.train_deploy_log(),
    statuses.TRAINING: deployment.train_log(),
    statuses.DONE_TRAINING: deployment.train_log(),
    statuses.BUILDING_FOR_API: deployment.api_deploy_log(),
    statuses.PREDICTING_SCHEDULED: deployment.api_deploy_log(),
    statuses.PREDICTING: deployment.api_deploy_log()
  }.get(curr_stage)

  return log_stream_key, curr_stage