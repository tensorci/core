# import gevent
# from socketio_client.manager import Manager
# from gevent import monkey
#
# monkey.patch_socket()
#
# io = Manager('http', 'localhost', 5000)
# ns = io.socket('/pass_through')
#
#
# @ns.on_connect()
# def ns_connect():
#   print('CONNECTED')
#   import code;
#   code.interact(local=locals())
#
#
# io.connect()
#
# # gevent.wait()
#
# print 'asdfasdfas'
#
#
# # import logging
# # import os
# # from src.config import config
# # from socketIO_client import SocketIO, BaseNamespace
# #
# # logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
# # logging.basicConfig()
# #
# #
# # # Define our custom namespace
# # class PassThroughNamespace(BaseNamespace):
# #   def on_pass_through_response(self, *args):
# #     print('Pass-through response: {}'.format(args))
# #
# # # Get a socket.io client instance
# # socket_client = SocketIO(config.SOCKET_URL, 5000)
# #
# # # Define the namespaces we want to use
# # pass_through_ns = socket_client.define(PassThroughNamespace, '/pass_through')
# #
# # # socket_client.wait(seconds=1)
# #
# #
# # def pass_through(payload=None, new_namespace='/'):
# #   data = {
# #     'payload': payload or {},
# #     'new_namespace': new_namespace
# #   }
# #
# #   try:
# #     pass_through_ns.emit('pass_through', data)
# #   except BaseException as e:
# #     print('SocketIO Broadcasting Exception: {}'.format(e))
# #     return False
# #
# #   return True
# #
# #
