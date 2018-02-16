import json
import threading
from pyredis import redis
from src.helpers.definitions import sse_broadcast_queue


class SSEBroadcaster(object):

  def __init__(self, socket):
    thread = threading.Thread(target=self.perform, kwargs={'socket': socket})
    thread.daemon = True
    thread.start()

  def perform(self, socket=None):
    while True:
      item = redis.blpop(sse_broadcast_queue, timeout=30)

      if not item:
        continue

      item = json.loads(item[1]) or {}

      if not item:
        continue

      payload = item.get('payload', {})
      namespace = item.get('namespace')

      if not payload or not namespace:
        continue

      try:
        socket.emit('message', payload, namespace=namespace)
      except BaseException as e:
        print('SSE Broadcast Error: {}'.format(e.__dict__))