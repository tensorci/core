import os
from redis import StrictRedis

redis = StrictRedis.from_url(url=os.environ.get('REDIS_URL'))