from kubernetes import client, config


def deploy(name, image=None, cluster=None, replicas=3):
  config.load_kube_config()

  container = config_container(name, image, cluster)

  template = config_template_spec(name, container)

  deploy_spec = config_deploy_spec(template, replicas)

  deployment = create_deployment(name, deploy_spec)

  api = api_instance()

  resp = api.create_namespaced_deployment(
    namespace='default',
    body=deployment
  )

  print('Deployment status: {}'.format(resp.status))


def api_instance():
  return client.ExtensionsV1beta1Api()


def config_container(name, image, cluster):
  ports = None

  # We only need to open ports for the API cluster
  if cluster == 'api':
    ports = [client.V1ContainerPort(container_port=80)]

  return client.V1Container(
    name=name,
    image=image,
    ports=ports
  )


def config_template_spec(name, container):
  return client.V1PodTemplateSpec(
    metadata=client.V1ObjectMeta(labels={'app': name}),
    spec=client.V1PodSpec(containers=[container])
  )


def config_deploy_spec(template, replicas):
  return client.ExtensionsV1beta1DeploymentSpec(
    replicas=replicas,
    template=template
  )


def create_deployment(name, deploy_spec):
  return client.ExtensionsV1beta1Deployment(
    api_version='extensions/v1beta1',
    kind='Deployment',
    metadata=client.V1ObjectMeta(name=name),
    spec=deploy_spec
  )