from rq import Queue
from pyredis import redis
import os


class JobQueue(object):

  def __init__(self, *args, **kwargs):
    self.q = Queue(*args, **kwargs)

  def add(self, job, *args, **kwargs):
    if os.environ.get('DELAYED_JOBS_SYNCHRONOUS'):
      return job(*args, **kwargs)

    return self.q.enqueue(job, *args, **kwargs)


job_queue = JobQueue(connection=redis, default_timeout=1800)