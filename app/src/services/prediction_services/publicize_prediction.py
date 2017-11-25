import os
from src import dbi
from src.utils import clusters
from src.utils.aws import add_dns_records
from kubernetes import client, config


class PublicizePrediction(object):

  def __init__(self, prediction=None, port=80, target_port=80):
    self.prediction = prediction
    self.port = port
    self.target_port = target_port
    self.team = self.prediction.team
    self.cluster = self.team.cluster.name
    self.client = client
    self.config = config
    self.deploy_name = '{}-{}'.format(self.prediction.slug, clusters.API)
    self.service_name = self.deploy_name

  def perform(self):
    self.config.load_kube_config(context=self.cluster)



    # create the elb

    api = self.client.CoreV1Api()

    service = self.client.V1Service(api_version='v1', kind='Service')

    service.metadata = self.client.V1ObjectMeta(name=self.service_name)

    service.spec = self.create_service_spec()

    api.create_namespaced_service(namespace='default', body=service)

    # Add elb to prediction
    # self.prediction = dbi.update(self.prediction, {'elb': elb})

    # Create a CNAME record for your subdomain with the ELB's url
    # add_dns_records(os.environ.get('TL_HOSTED_ZONE_ID'), self.prediction.domain, [elb], 'CNAME')

    # Validate that it works after a sec with a simple request

  def create_service_spec(self):
    spec = self.client.V1ServiceSpec()
    spec.selector = {'app': self.service_name}

    if self.port and self.target_port:
      spec.ports = [self.client.V1ServicePort(protocol='TCP', port=self.port, target_port=self.target_port)]

    # Create and add an ELB to the spec

    return spec
