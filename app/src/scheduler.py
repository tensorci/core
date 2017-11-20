from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from pytz import utc
from config import get_config

config = get_config()

jobstores = {
  'default': SQLAlchemyJobStore(url=config.SQLALCHEMY_DATABASE_URI)
}

executors = {
  'default': ThreadPoolExecutor(20),
  'processpool': ProcessPoolExecutor(5)
}

job_defaults = {
  'coalesce': True,
  'max_instances': 5
}

delayed = BackgroundScheduler(jobstores=jobstores, executors=executors,
                              job_defaults=job_defaults, timezone=utc)


def delay_class_method(klass=None, init_args={}, method_name='perform', method_args={}):
  class_instance = klass(**init_args)
  method = getattr(class_instance, method_name)
  method(**method_args)