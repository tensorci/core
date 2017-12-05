import os
from redis import StrictRedis

redis_url = os.environ.get('REDIS_URL')

if redis_url:
  redis = StrictRedis.from_url(url=redis_url)
else:
  redis = None