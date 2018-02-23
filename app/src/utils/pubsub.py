import os
from pubnub.exceptions import PubNubException
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from src import logger

pnconfig = PNConfiguration()
pnconfig.subscribe_key = os.environ.get('PUBNUB_SUBSCRIBE_KEY')
pnconfig.publish_key = os.environ.get('PUBNUB_PUBLISH_KEY')
pnconfig.ssl = True

pubnub = PubNub(pnconfig)


def publish(channel=None, data=None):
  try:
    pubnub.publish().channel(channel).message(data).sync()
  except PubNubException as e:
    logger.error('PubNubException: {}'.format(e))