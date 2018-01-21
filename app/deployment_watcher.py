import json
from src.utils.pyredis import redis
from src import dbi
from src.models import Deployment
from src.helpers import deployment_helper
from src.utils import pubsub
from src.helpers.definitions import deploy_update_queue


def handle_update(item):
  item = json.loads(item[1]) or {}

  if not item:
    return

  deployment_uid = item.get('deployment_uid')
  stage = item.get('stage')

  if not deployment_uid or not stage:
    return

  # Get the format stage function for this stage from deployment_helper
  format_stage_func_name = 'format_{}_stage'.format(stage)

  # Make sure the function even exists...
  if not hasattr(deployment_helper, format_stage_func_name):
    return

  # Get deployment for uid
  deployment = dbi.find_one(Deployment, {'uid': deployment_uid})

  if not deployment:
    return

  # Get the most recent formatted stage info for this stage/deployment
  stage_info = getattr(deployment_helper, format_stage_func_name)(deployment)

  # Broadcast this update to any clients listening
  pubsub.publish(channel=deployment_uid, data={stage: stage_info})


def watch():
  while True:
    item = redis.blpop(deploy_update_queue, timeout=30)

    if not item:
      continue

    try:
      handle_update(item)
    except BaseException as e:
      print(e.__dict__)


if __name__ == '__main__':
  watch()