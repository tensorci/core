from src import socket, logger


def publish(channel=None, data=None):
  try:
    socket.emit('message', data=data, namespace='/{}'.format(channel))
  except BaseException as e:
    logger.error('SocketIO Broadcasting Exception: {}'.format(e))
    return False

  return True