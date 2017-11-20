import os
from helpers.env import env


class Config:
  DEBUG = True
  SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProdConfig(Config):
  DEBUG = False
  DOMAIN = 'app.glimpse.ai'
  IMAGE_REPO_OWNER = 'glimpseprod'

  def __init__(self):
    self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


class StagingConfig(Config):
  DOMAIN = 'app.staging.glimpse.ai'
  IMAGE_REPO_OWNER = 'glimpsestaging'

  def __init__(self):
    self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


class DevConfig(Config):
  DOMAIN = 'app.dev.glimpse.ai'
  IMAGE_REPO_OWNER = 'glimpsedev'

  def __init__(self):
    self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


class TestConfig(Config):
  DOMAIN = 'app.test.glimpse.ai'
  IMAGE_REPO_OWNER = 'glimpsetest'

  def __init__(self):
    self.SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DB_URL')


def get_config():
  config_class = globals().get('{}Config'.format(env().capitalize()))
  return config_class()