import json
from pyredis import redis
from src.helpers import ms_since_epoch
from src.helpers.definitions import deploy_update_queue


class Logger(object):

  def __init__(self, base_logger=None):
    self.base_logger = base_logger

  def info(self, text, **kwargs):
    self.log(text, 'info', **kwargs)

  def warn(self, text, **kwargs):
    self.log(text, 'warn', **kwargs)

  def error(self, text, **kwargs):
    self.log(text, 'error', **kwargs)

  def log(self, text, level, **kwargs):
    # Always log to TensorCI internal logs
    if self.base_logger and hasattr(self.base_logger, level):
      getattr(self.base_logger, level)(text)
    else:
      print(text)

    # If redis stream should be piped into, do that as well
    if kwargs.get('stream'):
      stream = kwargs.pop('stream')

      redis.xadd(stream,
                 text=text,
                 level=level,
                 ts=ms_since_epoch(),
                 **kwargs)

      stream_key_comps = stream.split(':')
      deployment_uid = None
      stage = kwargs.get('stage')

      if len(stream_key_comps) == 2:
        deployment_uid = stream_key_comps.pop()

      if deployment_uid and stage:
        payload = {'deployment_uid': deployment_uid, 'stage': stage}
        redis.rpush(deploy_update_queue, json.dumps(payload))
