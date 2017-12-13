import os
from src import dbi, logger
from src.models import Deployment
from src.utils.aws import add_dns_records
from time import sleep
import requests
from kubernetes import client, config
from src.utils import kubectl


class PublicizePrediction(object):

  def __init__(self, deployment_uid=None, port=80, target_port=80):
    self.deployment_uid = deployment_uid
    self.port = port
    self.target_port = target_port
    self.deployment = None
    self.prediction = None
    self.team = None
    self.cluster = None
    self.cluster_name = None
    self.deploy_name = None
    self.service_name = None

  def perform(self):
    self.set_db_reliant_attrs()

    # Expose deployment with a LoadBalancer service
    exposed = kubectl.expose(resource='deployment/{}'.format(self.deploy_name),
                             port=self.port,
                             target_port=self.target_port,
                             name=self.service_name,
                             context=self.cluster_name,
                             cluster=self.cluster_name)

    if not exposed:
      return

    # Annotate service with SSL Cert if port is 443
    if self.port == 443:
      sleep(3)

      service_labels = {
        'service.beta.kubernetes.io/aws-load-balancer-ssl-cert': os.environ.get('WILDCARD_SSL_CERT_ARN'),
        'service.beta.kubernetes.io/aws-load-balancer-ssl-ports': self.port
      }

      annotated = kubectl.annotate(resource='service',
                                   resource_name=self.service_name,
                                   labels=service_labels,
                                   context=self.cluster_name,
                                   cluster=self.cluster_name)

      if not annotated:
        return

    # We need the CoreV1Api to poll our services
    api_client = config.new_client_from_config(context=self.cluster_name)
    self.api = client.CoreV1Api(api_client=api_client)

    # Get ELB for service
    elb_url = self.wait_for_elb()

    # Update the prediction record with the ELB's url
    self.prediction = dbi.update(self.prediction, {'elb': elb_url})

    # Create a CNAME record for your subdomain with the ELB's url
    add_dns_records(os.environ.get('TL_HOSTED_ZONE_ID'), self.prediction.domain, [elb_url], 'CNAME')

    logger.info('Waiting for TTL (60s)...', queue=self.deployment_uid)
    sleep(60)

    # Ping the url until the hostname is resolved
    self.poll_url()

    logger.info('Prediction live at https://{}/api/predict'.format(self.prediction.domain), queue=self.deployment_uid)

    # Update the deployment to its final status: PREDICTING
    dbi.update(self.deployment, {'status': self.deployment.statuses.PREDICTING})

  def wait_for_elb(self):
    elb = self.get_elb()

    if not elb:
      sleep(5)
      return self.wait_for_elb()

    return elb

  def get_elb(self):
    try:
      service_list = self.api.list_namespaced_service(
        namespace='default',
        label_selector='app={}'.format(self.deploy_name)
      )

      items = service_list.items or []
    except:
      return None

    if not items:
      return None

    service = items[0]
    service_status = service.status

    if not service.status:
      return None

    lb = service_status.load_balancer

    if not lb:
      return None

    ingress_list = lb.ingress

    if not ingress_list:
      return None

    return ingress_list[0].hostname

  def poll_url(self):
    connection_success = self.attempt_connection()

    if not connection_success:
      sleep(60)
      return self.poll_url()

    return None

  def attempt_connection(self):
    url = 'https://{}'.format(self.prediction.domain)
    logger.info('Pinging url {}...'.format(url), queue=self.deployment_uid)

    try:
      requests.get(url)
    except requests.exceptions.ConnectionError:
      return False

    return True

  def set_db_reliant_attrs(self):
    self.deployment = dbi.find_one(Deployment, {'uid': self.deployment_uid})
    self.prediction = self.deployment.prediction
    self.team = self.prediction.team
    self.cluster = self.team.cluster
    self.cluster_name = self.cluster.name
    self.deploy_name = self.prediction.deploy_name
    self.service_name = self.deploy_name