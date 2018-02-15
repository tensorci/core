import json
import threading
from pyredis import redis
from src.helpers.definitions import sse_broadcast_queue


class SSEBroadcaster(object):

  def __init__(self, socket):
    self.socket = socket
    thread = threading.Thread(target=self.perform, args=())
    thread.daemon = True
    thread.start()

  def perform(self):
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
        self.socket.emit('message',
                         data=payload,
                         namespace=namespace,
                         broadcast=True)
      except BaseException as e:
        print('SSE Broadcast Error: {}'.format(e.__dict__))