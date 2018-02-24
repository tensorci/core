from kubernetes import client, config
from src import dbi, logger
from src.models import Deployment
from src.services.cluster_services.export_cluster import ExportCluster
from src.utils import clusters


class ApiUpdate(object):

  def __init__(self, deployment_uid=None):
    self.deployment_uid = deployment_uid
    self.deployment = None
    self.repo = None
    self.cluster = None
    self.log_stream_key = None
    self.stage = None
    self.namespace = 'default'

  def deploy(self):
    self.set_db_reliant_attrs()

    self.log_stream_key = self.deployment.api_deploy_log()
    self.stage = self.deployment.statuses.PREDICTING_SCHEDULED

    # Ensure cluster/context exists in KUBECONFIG
    context_exported = ExportCluster(cluster=self.cluster).perform()

    if not context_exported:
      logger.error('Failure exporting cluster context.', stream=self.log_stream_key, stage=self.stage)
      return

    logger.info('Deploying...', stream=self.log_stream_key, section=True, stage=self.stage)

    spec = self.updated_deploy_spec()

    api_client = config.new_client_from_config(context=self.cluster.name)
    api = client.ExtensionsV1beta1Api(api_client=api_client)

    api.patch_namespaced_deployment(self.repo.deploy_name,
                                    namespace=self.namespace,
                                    body=spec)

    self.register_as_predicting()

  def updated_deploy_spec(self):
    container_name = '{}-{}'.format(clusters.API, self.repo.uid)
    image = '{}/{}:{}'.format(self.repo.image_repo_owner, container_name, self.commit.sha)

    return {
      'spec': {
        'template': {
          'spec': {
            'containers': [
              {
                'name': container_name,
                'image': image
              }
            ]
          }
        }
      }
    }

  def register_as_predicting(self):
    # Update deployment status to PREDICTING
    new_status = self.deployment.statuses.PREDICTING

    logger.info('Updating Deployment(sha={}) of Repo(slug={}) to status: {}.'.format(
      self.commit.sha, self.repo.slug, new_status))

    self.deployment = dbi.update(self.deployment, {'status': new_status})

    logger.info('Successfully deployed to API.', stream=self.log_stream_key, stage=self.stage)

    logger.info('Prediction live at https://{}/api/predict'.format(self.repo.domain),
                stream=self.log_stream_key,
                stage=self.stage,
                last_entry=True)

  def set_db_reliant_attrs(self):
    self.deployment = dbi.find_one(Deployment, {'uid': self.deployment_uid})
    self.commit = self.deployment.commit
    self.repo = self.deployment.repo
    self.cluster = self.repo.team.cluster