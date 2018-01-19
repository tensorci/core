import pytz
from src.helpers import ms_since_epoch
from datetime import datetime
from colors import *


def deploy_log(log):
  text = log.get('text')

  if not text:
    return '\n'

  if log.get('level') == 'error':
    prefix = '[ERROR] '
  elif log.get('level') == 'warn':
    prefix = '  !    '
  elif log.get('section'):
    prefix = ' ----> '
  else:
    prefix = '       '

  return prefix + text + '\n'


def training_log(log, with_color=False, with_ts=True):
  text = log.get('text')

  if not text:
    return '\n'

  if with_ts:
    ms = float(log.get('ts')) or ms_since_epoch()
    prefix = datetime.fromtimestamp(ms / 1000.0, pytz.utc).strftime('%Y-%m-%dT%H:%M:%S.%f') + ' '
  else:
    prefix = ''

  method = log.get('method')

  if method:
    prefix += '[{}]:'.format(method)

    if with_color:
      prefix = colorize(prefix, method)
  else:
    if prefix:
      prefix += ':'

  return '{} {}\n'.format(prefix, text)


def colorize(text, method):
  if method == 'prepro_data':
    return color(text, fg='yellow')

  if method == 'train':
    return color(text, fg='green')

  if method == 'test':
    return color(text, fg='cyan')

  return text