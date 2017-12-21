import json
from pyredis import redis
from src.helpers import ms_since_epoch


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
    if self.base_logger and hasattr(self.base_logger, level):
      getattr(self.base_logger, level)(text)
    else:
      print(text)

    if kwargs.get('queue'):
      data = {
        'text': text,
        'level': level,
        'complete': kwargs.get('last_entry'),
        'ts': ms_since_epoch(),
        'section': kwargs.get('section')
      }

      redis.rpush(kwargs.get('queue'), json.dumps(data))