import pytz
from src.helpers import ms_since_epoch
from datetime import datetime


def deploy_log(log):
  text = log.get('text')

  if not text:
    return '\n'

  if log.get('level') == 'error':
    prefix = '[ERROR] '
  elif log.get('level') == 'warn':
    prefix = ' !     '
  elif log.get('section'):
    prefix = '-----> '
  else:
    prefix = '       '

  return prefix + text + '\n'


def training_log(log):
  text = log.get('text')

  if not text:
    return '\n'

  ms = int(log.get('ts') or ms_since_epoch())
  dt = datetime.fromtimestamp(ms / 1000.0, pytz.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')

  prefix = dt

  if log.get('method'):
    prefix += ' [{}]'.format(log.get('method'))

  return '{}: {}\n'.format(prefix, text)