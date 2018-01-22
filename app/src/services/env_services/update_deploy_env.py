from src import dbi, logger
from src.models import Repo
from kubernetes import client, config
from src.utils import clusters
from src.helpers.deployment_helper import api_deploy_envs
from src.services.cluster_services.export_cluster import ExportCluster


class UpdateDeployEnv(object):

  def __init__(self, repo_uid=None):
    self.repo_uid = repo_uid
    self.repo = None
    self.cluster = None
    self.container_name = '{}-{}'.format(clusters.API, repo_uid)
    self.image = None
    self.namespace = 'default'

  def perform(self):
    # Set attrs reliant on db queries (and blow up if records not found)
    self.set_db_reliant_attrs()

    # Ensure cluster/context exists in KUBECONFIG
    context_exported = ExportCluster(cluster=self.cluster).perform()

    if not context_exported:
      raise BaseException('Failure exporting context for Cluster(id={}).'.format(self.cluster.id))

    # Get the new deploy spec with updated envs
    body = self.new_deploy_body()

    # Get api client instance
    api_client = config.new_client_from_config(context=self.cluster.name)
    api = client.ExtensionsV1beta1Api(api_client=api_client)

    # Patch the deployment with the new spec
    api.patch_namespaced_deployment(self.repo.deploy_name,
                                    namespace=self.namespace,
                                    body=body)

  def new_deploy_body(self):
    envs = api_deploy_envs(self.repo, cluster=self.cluster)

    for env in self.repo.api_envs():
      if env.name not in envs:
        envs[env.name] = env.value

    updated_envs = [client.V1EnvVar(name=n, value=v) for n, v in envs.iteritems()]

    return {
      'spec': {
        'template': {
          'spec': {
            'containers': [
              {
                'name': self.container_name,
                'image': self.image,
                'envs': updated_envs
              }
            ]
          }
        }
      }
    }

  def set_db_reliant_attrs(self):
    self.repo = dbi.find_one(Repo, {'uid': self.repo_uid})

    if not self.repo:
      raise BaseException('Not updating deploy env -- No repo exists for uid {}.'.format(self.repo_uid))

    self.cluster = self.repo.team.cluster

    # Find latest API deployment for this repo and get its commit SHA
    deployment = None
    for dep in self.repo.ordered_deployments():
      if not dep.failed and dep.intent_to_serve():
        deployment = dep
        break

    if not deployment:
      raise BaseException('Not updating deploy env -- No unfailed deployment with intent to serve '
                          'exists for Repo(uid={})'.format(self.repo_uid))

    self.image = '{}/{}:{}'.format(self.repo.image_repo_owner, self.container_name, deployment.commit.sha)
