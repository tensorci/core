import json
from src.utils.pyredis import redis


class DeploymentLogger(object):

  def __init__(self, deployment):
    self.deployment = deployment

  def log_to_redis(func):
    def wrapper(self, text, **kwargs):
      data = {
        'text': text,
        'complete': kwargs.get('complete') == True
      }

      redis.rpush(self.deployment.uid, json.dumps(data))

      return func(self, text, **kwargs)

    return wrapper

  # TODO: Figure out specific use-cases for the these three functions. Otherwise, combine them.

  @log_to_redis
  def info(self, text, **kwargs):
    pass

  @log_to_redis
  def warn(self, text, **kwargs):
    pass

  @log_to_redis
  def error(self, text, **kwargs):
    pass