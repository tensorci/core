import os
from helpers.env import env


class Config:
  DEBUG = True
  SQLALCHEMY_TRACK_MODIFICATIONS = False
  CLUSTER_NODE_COUNT = 3


class ProdConfig(Config):
  DEBUG = False
  DOMAIN = 'tensorci.com'
  IMAGE_REPO_OWNER = 'tensorci'

  def __init__(self):
    self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    self.CORE_URL = os.environ.get('CORE_URL') or 'https://app.{}/api'.format(self.DOMAIN)


class StagingConfig(Config):
  DEBUG = False
  DOMAIN = 'staging.tensorci.com'
  IMAGE_REPO_OWNER = 'tensorcistaging'

  def __init__(self):
    self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    self.CORE_URL = os.environ.get('CORE_URL') or 'https://app.{}/api'.format(self.DOMAIN)


class DevConfig(Config):
  DOMAIN = 'dev.tensorci.com'
  IMAGE_REPO_OWNER = 'tensorcidev'

  def __init__(self):
    self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    self.CORE_URL = os.environ.get('CORE_URL') or 'https://app.{}/api'.format(self.DOMAIN)


class TestConfig(Config):
  DOMAIN = 'localhost'
  IMAGE_REPO_OWNER = 'tensorcitest'

  def __init__(self):
    self.SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DB_URL')
    self.CORE_URL = os.environ.get('CORE_URL') or 'http://localhost/api'


def get_config():
  config_class = globals().get('{}Config'.format(env().capitalize()))
  return config_class()


config = get_config()