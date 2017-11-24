import os
from helpers.env import env


class Config:
  DEBUG = True
  SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProdConfig(Config):
  DEBUG = False
  DOMAIN = 'app.tensorci.com'
  IMAGE_REPO_OWNER = 'tensorci-prod'

  def __init__(self):
    self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


class StagingConfig(Config):
  DOMAIN = 'app.staging.tensorci.com'
  IMAGE_REPO_OWNER = 'tensorci-staging'

  def __init__(self):
    self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


class DevConfig(Config):
  DOMAIN = 'app.dev.tensorci.com'
  IMAGE_REPO_OWNER = 'tensorci-dev'

  def __init__(self):
    self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


class TestConfig(Config):
  DOMAIN = 'app.test.tensorci.com'
  IMAGE_REPO_OWNER = 'tensorci-test'

  def __init__(self):
    self.SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DB_URL')


def get_config():
  config_class = globals().get('{}Config'.format(env().capitalize()))
  return config_class()