from kubernetes import client, config
from src.utils import clusters


class AbstractDeploy(object):

  def __init__(self, prediction=None):
    self.prediction = prediction
    self.team = prediction.team
    self.api = client.ExtensionsV1beta1Api()
    self.client = client
    self.config = config

    # Overwritten in child class
    self.image = None
    self.name = None
    self.replicas = 1
    self.namespace = 'default'
    self.cluster = None
    self.envs = {}

  def deploy(self):
    self.config.load_kube_config()

    # TODO: Figure out where to put self.envs
    container = self.config_container()
    template = self.config_template_spec(container)
    deploy_spec = self.config_deploy_spec(template)
    deployment = self.create_deployment(deploy_spec)

    return self.api.create_namespaced_deployment(
      namespace=self.namespace,
      body=deployment
    )

  def config_container(self):
    ports = None

    if self.cluster == clusters.API:
      ports = [self.client.V1ContainerPort(container_port=80)]

    return self.client.V1Container(
      name=self.name,
      image=self.image,
      ports=ports
    )

  def config_template_spec(self, container):
    return self.client.V1PodTemplateSpec(
      metadata=self.client.V1ObjectMeta(labels={'app': self.name}),
      spec=self.client.V1PodSpec(containers=[container])
    )

  def config_deploy_spec(self, template):
    return self.client.ExtensionsV1beta1DeploymentSpec(
      replicas=self.replicas,
      template=template
    )

  def create_deployment(self, deploy_spec):
    return self.client.ExtensionsV1beta1Deployment(
      api_version='extensions/v1beta1',
      kind='Deployment',
      metadata=self.client.V1ObjectMeta(name=self.name),
      spec=deploy_spec
    )