import log_formatter
from src import logger, dbi
from pyredis import redis
from src.helpers.definitions import tci_keep_alive


def should_complete_stream(data, deployment):
  # Check if last_entry was specified in the log. Complete the stream if so.
  complete = data.get('last_entry') == 'True'

  # Check to see if this was an error log. Complete the stream if so.
  if data.get('level') == 'error':
    # Fail the deployment and log that this happened internally
    logger.error('DEPLOYMENT FAILED: uid={}'.format(deployment.uid))
    deployment.fail()
    complete = True

  return complete


def stream_deploy_logs(deployment, stream_key=None, block=30000):
  complete = False
  first_log = redis.xrange(stream_key, count=1)
  
  # If logs already exist, yield the first one and then
  # iterate over timestamps to continue yielding
  if first_log:
    ts, data = first_log[0]
    first_log_yielded = False

    while not complete:
      try:
        # yield the first log and continue
        if not first_log_yielded:
          first_log_yielded = True
          complete = should_complete_stream(data, deployment)
          yield log_formatter.deploy_log(data)
          continue

        # Get all logs since timestamp=ts
        result = redis.xread(block=block, **{stream_key: ts})

        if not result:
          yield tci_keep_alive + '\n'
          continue

        items = result.get(stream_key)

        if not items:
          yield tci_keep_alive + '\n'
          continue

        for item in items:
          ts, data = item
          complete = should_complete_stream(data, deployment)
          yield log_formatter.deploy_log(data)
      except:
        break
  else:
    while not complete:
      try:
        item = redis.xread(stream_key, block=block)

        if not item:
          yield tci_keep_alive + '\n'
          continue

        ts, data = item[0]
        complete = should_complete_stream(data, deployment)
        yield log_formatter.deploy_log(data)
      except:
        break


def stream_train_logs(deployment, block=30000):
  stream_key = deployment.train_log()
  first_log = redis.xrange(stream_key, count=1)

  # If logs already exist, yield the first one and then
  # iterate over timestamps to continue yielding
  if first_log:
    ts, data = first_log[0]
    first_log_yielded = False

    while True:
      try:
        # yield the first log and continue
        if not first_log_yielded:
          first_log_yielded = True
          yield log_formatter.training_log(data, with_color=True)
          continue

        # Get all logs since timestamp=ts
        result = redis.xread(block=block, **{stream_key: ts})

        if not result:
          yield tci_keep_alive + '\n'
          continue

        items = result.get(stream_key)

        if not items:
          yield tci_keep_alive + '\n'
          continue

        for item in items:
          ts, data = item
          yield log_formatter.training_log(data, with_color=True)
      except:
        break
  else:
    while True:
      try:
        item = redis.xread(stream_key, block=block)

        if not item:
          yield tci_keep_alive + '\n'
          continue

        ts, data = item[0]
        yield log_formatter.training_log(data, with_color=True)
      except:
        break