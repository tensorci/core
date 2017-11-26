from kubernetes import client, config
from src import dbi
from src.models import Prediction


class AbstractDeploy(object):

  def __init__(self, prediction_uid=None):
    self.prediction_uid = prediction_uid
    self.prediction = dbi.find_one(Prediction, {'uid': prediction_uid})
    self.team = self.prediction.team
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
    self.job = False
    self.restart_policy = 'Always'
    self.volume_mounts = None
    self.volumes = None

  def deploy(self):
    # Configure k8s to deploy to our desired cluster
    self.config.load_kube_config(context=self.cluster)

    # Create a container spec
    container = self.create_container()

    # Add the container spec to a pod spec
    pod_template = self.create_template_spec([container])

    # Create deployment object
    deployment = self.create_deployment(pod_template)

    # Get ref to the proper deploy method on appropriate api
    deploy_method = self.get_deploy_method()

    # Execute deploy
    deploy_resp = deploy_method(namespace=self.namespace, body=deployment)

    return deploy_resp

  def create_container(self):
    ports = None
    volume_mounts = None

    if self.ports:
      ports = [self.client.V1ContainerPort(container_port=p) for p in self.ports]

    if self.volume_mounts:
      volume_mounts = [self.client.V1VolumeMount(**m) for m in self.volume_mounts]

    container_name = self.deploy_name

    envs = [self.client.V1EnvVar(name=n, value=v) for n, v in self.envs.iteritems()]

    return self.client.V1Container(
      name=container_name,
      image=self.image,
      ports=ports,
      env=envs,
      volume_mounts=volume_mounts
    )

  def create_template_spec(self, containers):
    volumes = None

    if self.volumes:
      volumes = []
      for v in self.volumes:
        vol = self.client.V1Volume(name=v.get('name'))

        if v.get('type') == 'host_path':
          vol.host_path = self.client.V1HostPathVolumeSource(path=v.get('path'))

        volumes.append(vol)

    metadata = self.client.V1ObjectMeta(labels={'app': self.deploy_name})

    spec = self.client.V1PodSpec(
      containers=containers,
      volumes=volumes,
      restart_policy=self.restart_policy
    )

    return self.client.V1PodTemplateSpec(
      metadata=metadata,
      spec=spec
    )

  def create_deployment(self, template):
    metadata = self.client.V1ObjectMeta(name=self.deploy_name)

    if self.job:
      deployment = self.client.V1Job(
        api_version='batch/v1',
        kind='Job',
        metadata=metadata,
        spec=template
      )
    else:
      deploy_spec = self.client.ExtensionsV1beta1DeploymentSpec(
        replicas=self.replicas,
        template=template
      )

      deployment = self.client.ExtensionsV1beta1Deployment(
        api_version='extensions/v1beta1',
        kind='Deployment',
        metadata=metadata,
        spec=deploy_spec
      )

    return deployment

  def get_deploy_method(self):
    if self.job:
      api = self.client.BatchV1Api()
      method = api.create_namespaced_job
    else:
      api = self.client.ExtensionsV1beta1Api()
      method = api.create_namespaced_deployment

    return method