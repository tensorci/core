from kubernetes import client, config
from src import dbi
from src.models import Prediction


class AbstractDeploy(object):

  def __init__(self, prediction_uid=None):
    self.prediction_uid = prediction_uid
    self.prediction = dbi.find_one(Prediction, {'uid': prediction_uid})
    self.team = self.prediction.team
    self.api = client.ExtensionsV1beta1Api()
    self.client = client
    self.config = config

    # Overwritten in child class
    self.image = None
    self.deploy_name = None
    self.cluster = None
    self.ports = None
    self.replicas = 1
    self.namespace = 'default'
    self.envs = {}

  def deploy(self):
    # Configure k8s to deploy to our desired cluster
    self.config.load_kube_config(context=self.cluster)

    # Create a container spec
    container = self.config_container()

    # Add the container spec to a pod spec
    pod_template = self.config_template_spec(container)

    # Create a deployment spec
    deploy_spec = self.config_deploy_spec(pod_template)

    # Create a deployment object
    deployment = self.create_deployment(deploy_spec)

    # Perform deploy
    deploy_resp = self.api.create_namespaced_deployment(
      namespace=self.namespace,
      body=deployment
    )

    return deploy_resp

  def config_container(self):
    ports = None

    if self.ports:
      ports = [self.client.V1ContainerPort(container_port=p) for p in self.ports]

    container_name = self.deploy_name

    envs = []
    for name, value in self.envs.iteritems():
      envs.append(self.client.V1EnvVar(name=name, value=value))

    return self.client.V1Container(
      name=container_name,
      image=self.image,
      ports=ports,
      env=envs
    )

  def config_template_spec(self, container):
    return self.client.V1PodTemplateSpec(
      metadata=self.client.V1ObjectMeta(labels={'app': self.deploy_name}),
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
      metadata=self.client.V1ObjectMeta(name=self.deploy_name),
      spec=deploy_spec
    )