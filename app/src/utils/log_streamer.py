import json
import log_formatter
from src import logger, dbi
from pyredis import redis
from src.models import Deployment
from src.helpers.definitions import tci_keep_alive

# TODO: Abstract this out even further to be not as tightly coupled to deployments


def from_list(list_key):
  complete = False

  while not complete:
    item = redis.blpop(list_key, timeout=30)

    try:
      if not item:
        yield tci_keep_alive + '\n'
        continue

      item = json.loads(item[1])
      complete = item.get('last_entry') is True

      # if logger.error, update the deployment to failed=True
      if item.get('level') == 'error':
        complete = True
        deployment = dbi.find_one(Deployment, {'uid': list_key})

        if deployment:
          logger.error('DEPLOYMENT FAILED: {}'.format(list_key))
          deployment.fail()

      yield log_formatter.deploy_log(item)
    except:
      break


def from_stream(stream_key):
  block = 30000
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
          yield log_formatter.training_log(data)
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
          yield log_formatter.training_log(data)
      except:
        break
  else:
    while True:
      try:
        item = redis.xread(stream_key, block=30000)

        if not item:
          yield tci_keep_alive + '\n'
          continue

        ts, data = item[0]
        yield log_formatter.training_log(data)
      except:
        break