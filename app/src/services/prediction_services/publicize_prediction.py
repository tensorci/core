import os
from src import dbi, logger
from src.models import Deployment
from src.utils.aws import add_dns_records
from time import sleep
import requests
from kubernetes import client, config


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
    service_success = self.create_service()

    if not service_success:
      return

    # We need the CoreV1Api to list_namespaced_service
    api_client = config.new_client_from_config(context=self.cluster_name)

    self.api = client.CoreV1Api(api_client=api_client)

    # Get ELB for service
    elb_url = self.wait_for_elb()

    # Update the prediction record with the ELB's url
    self.prediction = dbi.update(self.prediction, {'elb': elb_url})

    # Create a CNAME record for your subdomain with the ELB's url
    add_dns_records(os.environ.get('TL_HOSTED_ZONE_ID'), self.prediction.domain, [elb_url], 'CNAME')

    logger.info('Waiting for TTL (60s)...')
    sleep(60)

    # Ping the url until the hostname is resolved
    self.poll_url()

    logger.info('Prediction live at https://{}/api/predict'.format(self.prediction.domain))

    dbi.update(self.deployment, {'status': self.deployment.statuses.PREDICTING})

  def create_service(self):
    try:
      # Create the service
      os.system('kubectl expose deployment/{} --type=LoadBalancer --port={} --target-port={} --name={} --context={} --cluster={}'.format(
        self.deploy_name, self.port, self.target_port, self.service_name, self.cluster_name, self.cluster_name))

      if self.port == 443:
        sleep(3)

        # Annotate service with SSL Cert
        os.system('kubectl annotate service {} service.beta.kubernetes.io/aws-load-balancer-ssl-cert={} service.beta.kubernetes.io/aws-load-balancer-ssl-ports={} --context={} --cluster={}'.format(
          self.service_name, os.environ.get('WILDCARD_SSL_CERT_ARN'), self.port, self.cluster_name, self.cluster_name))
    except BaseException as e:
      logger.error('Error creating service {} with error: {}'.format(self.service_name, e))
      return False

    return True

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
      sleep(20)
      return self.poll_url()

    return None

  def attempt_connection(self):
    url = 'https://{}'.format(self.prediction.domain)
    logger.info('Pinging url {}...'.format(url))

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