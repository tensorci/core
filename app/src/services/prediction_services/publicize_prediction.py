import os
import requests
from kubernetes import client, config
from src import dbi, logger
from src.deploys.api_worker_deploy import ApiWorkerDeploy
from src.models import Deployment
from src.services.cluster_services.export_cluster import ExportCluster
from src.utils import kubectl
from src.utils.aws import add_dns_records
from src.utils.job_queue import job_queue
from time import sleep


class PublicizePrediction(object):

  def __init__(self, deployment_uid=None, port=80, target_port=80,
               deploy_name=None, service_name=None, with_deploy=True):

    self.deployment_uid = deployment_uid
    self.port = port
    self.target_port = target_port
    self.deploy_name = deploy_name
    self.service_name = service_name
    self.with_deploy = with_deploy

    self.deployment = None
    self.repo = None
    self.team = None
    self.cluster = None

    self.cluster_name = None
    self.log_stream_key = None
    self.stage = None

  def perform(self):
    self.set_db_reliant_attrs()

    self.log_stream_key = self.deployment.api_deploy_log()
    self.stage = self.deployment.statuses.PREDICTING_SCHEDULED

    logger.info('Publicizing prediction (this only has to happen once)...',
                stream=self.log_stream_key,
                stage=self.stage,
                section=True)

    logger.info('Exposing deployment...', stream=self.log_stream_key, stage=self.stage)

    # Ensure cluster/context exists in KUBECONFIG
    context_exported = ExportCluster(cluster=self.cluster).perform()

    if not context_exported:
      logger.error('Failure exporting cluster context.', stream=self.log_stream_key, stage=self.stage)
      return

    # Expose deployment with a LoadBalancer service
    exposed = kubectl.expose(resource='deployment/{}'.format(self.deploy_name),
                             port=self.port,
                             target_port=self.target_port,
                             name=self.service_name,
                             context=self.cluster_name,
                             cluster=self.cluster_name)

    if not exposed:
      logger.error('Failure exposing deployment.', stream=self.log_stream_key, stage=self.stage)
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
        logger.error('Failure annotating service.', stream=self.log_stream_key, stage=self.stage)
        return

    # We need the CoreV1Api to poll our services
    api_client = config.new_client_from_config(context=self.cluster_name)
    self.api = client.CoreV1Api(api_client=api_client)

    # Get ELB for service
    elb_url = self.wait_for_elb()

    # Update the repo record with the ELB's url
    self.repo = dbi.update(self.repo, {'elb': elb_url})

    logger.info('Assigning url to prediction...', stream=self.log_stream_key, stage=self.stage)

    # Create a CNAME record for your subdomain with the ELB's url
    cname_record_added = add_dns_records(os.environ.get('TL_HOSTED_ZONE_ID'), self.repo.domain, [elb_url], 'CNAME')

    if not cname_record_added:
      logger.error('Failure upserting CNAME record for deployment.', stream=self.log_stream_key, stage=self.stage)
      return

    sleep(60)

    # Ping the url until the hostname is resolved
    self.poll_url()

    logger.info('Publication successful.', stream=self.log_stream_key, stage=self.stage)

    if self.with_deploy:
      logger.info('Spinning up workers...', stream=self.log_stream_key, stage=self.stage)

      api_worker_deployer = ApiWorkerDeploy(deployment_uid=self.deployment_uid)
      job_queue.add(api_worker_deployer.deploy, meta={'deployment': self.deployment_uid})

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
    url = 'https://{}'.format(self.repo.domain)
    logger.info('Pinging url until response...', stream=self.log_stream_key, stage=self.stage)

    try:
      requests.get(url)
    except requests.exceptions.ConnectionError:
      return False

    return True

  def set_db_reliant_attrs(self):
    self.deployment = dbi.find_one(Deployment, {'uid': self.deployment_uid})
    self.repo = self.deployment.repo
    self.team = self.repo.team
    self.cluster = self.team.cluster
    self.cluster_name = self.cluster.name