from rq import Queue
from pyredis import redis

if redis:
  job_queue = Queue(connection=redis)
else:
  job_queue = None