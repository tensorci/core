import os
from src import dbi, logger
from src.models import Team, Cluster, Deployment
from src.deploys.api_deploy import ApiDeploy
from src.utils.aws import create_route53_hosted_zone, add_dns_records, os_map
from src.utils import kops
from src.utils.job_queue import job_queue
from time import sleep
from src.config import config


class CreateCluster(object):

  def __init__(self, team_uid=None, deployment_uid=None, with_deploy=False):
    self.team_uid = team_uid
    self.deployment_uid = deployment_uid
    self.with_deploy = with_deploy
    self.team = None
    self.cluster = None
    self.bucket = None
    self.deployment = None
    self.log_stream_key = None
    self.stage = None

  def perform(self):
    self.set_db_reliant_attrs()

    logger.info('Creating API cluster (this only has to happen once)...',
                stream=self.log_stream_key,
                stage=self.stage,
                section=True)

    logger.info('Adding DNS records (this could take a minute)...', stream=self.log_stream_key, stage=self.stage)

    # Create Route53 hosted zone for cluster
    hosted_zone_id, ns_addresses = create_route53_hosted_zone(self.cluster.name)

    if not hosted_zone_id or not ns_addresses:
      logger.error('Failure upserting hosted zone.', stream=self.log_stream_key, stage=self.stage)
      return

    # Update the cluster with the Route53 info
    self.cluster = dbi.update(self.cluster, {
      'hosted_zone_id': hosted_zone_id,
      'ns_addresses': ns_addresses
    })

    # Register NS records for each of the ns_addresses with the TLD
    dns_success = add_dns_records(os.environ.get('TL_HOSTED_ZONE_ID'), self.cluster.name, ns_addresses, 'NS')

    if not dns_success:
      logger.error('Failure registering NS records for cluster.', stream=self.log_stream_key, stage=self.stage)
      return

    sleep(60)

    # Get S3 bucket url
    bucket_url = self.bucket.url()

    logger.info('Spinning up instances...', stream=self.log_stream_key, stage=self.stage)

    # Create cluster with kops
    cluster_created = kops.create_cluster(
      name=self.cluster.name,
      zones=','.join(self.cluster.zones),
      master_size=self.cluster.master_type,
      node_size=self.cluster.node_type,
      node_count=config.CLUSTER_NODE_COUNT,
      state=bucket_url,
      image=os_map.get(self.cluster.image),
      version=os.environ.get('K8S_VERSION')
    )

    if not cluster_created:
      logger.error('Failed to create cluster.', stream=self.log_stream_key, stage=self.stage)
      return

    logger.info('Validating cluster (this could take awhile)...', stream=self.log_stream_key, stage=self.stage)

    # Wait until our cluster is up and running
    self.validate_cluster(bucket_url)

    # Make an API deploy once cluster is validated (if desired)
    if self.with_deploy:
      logger.info('Scheduling deploy to API cluster...', stream=self.log_stream_key, section=True, stage=self.stage)
      sleep(5)

      api_deployer = ApiDeploy(deployment_uid=self.deployment_uid)
      job_queue.add(api_deployer.deploy, meta={'deployment': self.deployment_uid})

      self.deployment = dbi.find_one(Deployment, {'uid': self.deployment_uid})
      dbi.update(self.deployment, {'status': self.deployment.statuses.PREDICTING_SCHEDULED})

  def validate_cluster(self, state):
    while not kops.validate_cluster(name=self.cluster.name, state=state):
      logger.info('Pinging cluster until response...', stream=self.log_stream_key, stage=self.stage)
      sleep(120)

    # Register that the cluster is validated
    logger.info('Cluster successfully created.', stream=self.log_stream_key, stage=self.stage)

    dbi.update(self.cluster, {'validated': True})

  def set_db_reliant_attrs(self):
    self.team = dbi.find_one(Team, {'uid': self.team_uid})
    self.cluster = self.team.cluster
    self.bucket = self.cluster.bucket
    self.log_stream_key = self.deployment.api_deploy_log()
    self.stage = self.deployment.statuses.PREDICTING_SCHEDULED