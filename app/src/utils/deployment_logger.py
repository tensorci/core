import json
from src.utils.pyredis import redis


class DeploymentLogger(object):

  def __init__(self, logger, deployment=None):
    self.logger = logger
    self.deployment = deployment

  def log_to_redis(func):
    def wrapper(self, text, **kwargs):
      data = {
        'text': text,
        'complete': kwargs.get('complete')
      }

      redis.rpush(self.deployment.uid, json.dumps(data))

      return func(self, text, **kwargs)

    return wrapper

  @log_to_redis
  def info(self, text, **kwargs):
    self.logger.info(text)

  @log_to_redis
  def warn(self, text, **kwargs):
    self.logger.warn(text)

  @log_to_redis
  def error(self, text, **kwargs):
    self.logger.error(text)