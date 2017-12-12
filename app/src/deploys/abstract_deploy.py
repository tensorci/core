from kubernetes import client, config
from src import dbi, logger
from src.models import Deployment


class AbstractDeploy(object):

  def __init__(self, deployment_uid=None):
    self.deployment_uid = deployment_uid
    self.deployment = None
    self.prediction = None
    self.team = None
    self.cluster = None
    self.bucket = None

    self.api_client = None
    self.api = None

    # Overwritten in child class
    self.container_name = None
    self.image = None
    self.deploy_name = None
    self.cluster_name = None
    self.ports = None
    self.replicas = 1
    self.namespace = 'default'
    self.envs = None
    self.job = False
    self.restart_policy = 'Always'
    self.volume_mounts = None
    self.volumes = None

  def deploy(self):
    # Configure volume mounts
    volume_mounts = self.configure_volume_mounts()

    # Configure ports
    ports = self.configure_ports()

    # Configure environment variables
    envs = self.configure_envs()

    # Configure a container
    container = self.configure_container(volume_mounts=volume_mounts,
                                         ports=ports,
                                         envs=envs)

    # Configure volumes
    volumes = self.configure_volumes()

    # Build up: container --> pod spec --> pod template spec
    pod_template_spec = self.configure_pod_template_spec(containers=[container],
                                                         volumes=volumes)

    # Configure deploy spec
    deploy_spec = self.configure_deploy_spec(pod_template_spec)

    # Configure deploy object
    deploy_obj = self.configure_deploy_obj(deploy_spec)

    # Get an api_client for cluster's config, then use that to build the api
    api_client = config.new_client_from_config(context=self.cluster_name)

    if self.job:
      self.api = client.BatchV1Api(api_client=api_client)
      deploy_method = self.api.create_namespaced_job
    else:
      self.api = client.ExtensionsV1beta1Api(api_client=api_client)
      deploy_method = self.api.create_namespaced_deployment

    # Execute deploy
    deploy_method(namespace=self.namespace, body=deploy_obj)

    self.on_deploy_success()

  def configure_volume_mounts(self):
    if self.volume_mounts:
      return [client.V1VolumeMount(**m) for m in self.volume_mounts]

    return None

  def configure_ports(self):
    if self.ports:
      return [client.V1ContainerPort(container_port=p) for p in self.ports]

    return None

  def configure_envs(self):
    if self.envs:
      return [client.V1EnvVar(name=n, value=v) for n, v in self.envs.iteritems()]

    return None

  def configure_container(self, volume_mounts=None, ports=None, envs=None):
    return client.V1Container(
      name=self.container_name,
      image=self.image,
      ports=ports,
      env=envs,
      volume_mounts=volume_mounts
    )

  def configure_volumes(self):
    volumes = None

    if self.volumes:
      volumes = []

      for v in self.volumes:
        vol = client.V1Volume(name=v.get('name'))

        if v.get('type') == 'host_path':
          vol.host_path = client.V1HostPathVolumeSource(path=v.get('path'))

        volumes.append(vol)

    return volumes

  def configure_pod_template_spec(self, containers=None, volumes=None):
    metadata = client.V1ObjectMeta(labels={'app': self.deploy_name})

    pod_spec = client.V1PodSpec(
      containers=containers,
      volumes=volumes,
      restart_policy=self.restart_policy
    )

    return client.V1PodTemplateSpec(
      metadata=metadata,
      spec=pod_spec
    )

  def configure_deploy_spec(self, pod_template_spec):
    if self.job:
      deploy_spec = client.V1JobSpec(template=pod_template_spec)
    else:
      deploy_spec = client.ExtensionsV1beta1DeploymentSpec(
        replicas=self.replicas,
        template=pod_template_spec
      )

    return deploy_spec

  def configure_deploy_obj(self, deploy_spec):
    metadata = client.V1ObjectMeta(name=self.deploy_name)

    if self.job:
      deploy_obj = client.V1Job(
        api_version='batch/v1',
        kind='Job',
        metadata=metadata,
        spec=deploy_spec
      )
    else:
      deploy_obj = client.ExtensionsV1beta1Deployment(
        api_version='extensions/v1beta1',
        kind='Deployment',
        metadata=metadata,
        spec=deploy_spec
      )

    return deploy_obj

  def set_db_reliant_attrs(self):
    self.deployment = dbi.find_one(Deployment, {'uid': self.deployment_uid})
    self.prediction = self.deployment.prediction
    self.team = self.prediction.team
    self.cluster = self.team.cluster
    self.bucket = self.cluster.bucket

  def update_deployment_status(self, status):
    logger.info('Updating Deployment(sha={}) of Prediction(slug={}) to status: {}.'.format(
      self.deployment.sha, self.prediction.slug, status), queue=self.deployment_uid)

    self.deployment = dbi.update(self.deployment, {'status': status})

  def on_deploy_success(self):
    pass