import os
from abstract_deploy import AbstractDeploy
from src.utils import deployer, image_names, clusters
from src.config import get_config

config = get_config()


class BuildServerDeploy(AbstractDeploy):

  def __init__(self, prediction, build_for=None):
    self.prediction = prediction
    self.team = prediction.team
    self.build_for = build_for

  def perform(self):
    envs = {
      'DOCKER_USERNAME': os.environ.get('DOCKER_USERNAME'),
      'DOCKER_PASSWORD': os.environ.get('DOCKER_PASSWORD'),
      'CORE_URL': 'https://{}/api'.format(config.DOMAIN),
      'CORE_API_TOKEN': os.environ.get('CORE_API_TOKEN'),
      'TEAM': self.team.slug,
      'TEAM_UID': self.team.uid,
      'PREDICTION': self.prediction.slug,
      'PREDICTION_UID': self.prediction.uid,
      'GIT_REPO': self.prediction.git_repo,
      'IMAGE_OWNER': self.prediction.image_repo_owner,
      'FOR_CLUSTER': self.build_for
    }

    build_image = '{}/{}'.format(config.IMAGE_REPO_OWNER, image_names.BUILD_SERVER)
    deploy_name = '{}-{}-build'.format(self.prediction.slug, self.build_for)

    deployer.deploy(name=deploy_name,
                    image=build_image,
                    cluster=clusters.BUILD_SERVER,
                    envs=envs)