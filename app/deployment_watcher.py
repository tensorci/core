import json
from src.utils.pyredis import redis
from src import dbi
from src.models import Deployment
from src.helpers.deployment_helper import current_stage, format_stages
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

  # Get deployment for uid
  deployment = dbi.find_one(Deployment, {'uid': deployment_uid})

  if not deployment:
    return

  payload = {
    'readable_status': deployment.readable_status(),
    'intent': deployment.intent,
    'failed': deployment.failed,
    'succeeded': deployment.succeeded(),
    'current_stage': current_stage(deployment),
    'stages': format_stages(deployment)
  }

  pubsub.publish(channel=deployment_uid, data=payload)


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