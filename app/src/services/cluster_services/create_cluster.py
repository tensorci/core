import os
from src import dbi, logger
from src.models import Team, Cluster
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

  def perform(self):
    self.set_db_reliant_attrs()

    logger.info('Creating API cluster (this only has to happen once)...', queue=self.deployment_uid, section=True)
    logger.info('Adding DNS records (this could take a minute)...', queue=self.deployment_uid)

    # Create Route53 hosted zone for cluster
    hosted_zone_id, ns_addresses = create_route53_hosted_zone(self.cluster.name)

    # Update the cluster with the Route53 info
    self.cluster = dbi.update(self.cluster, {
      'hosted_zone_id': hosted_zone_id,
      'ns_addresses': ns_addresses
    })

    # Register NS records for each of the ns_addresses with the TLD
    dns_success = add_dns_records(os.environ.get('TL_HOSTED_ZONE_ID'), self.cluster.name, ns_addresses, 'NS')

    if not dns_success:
      return

    sleep(60)

    # Get S3 bucket url
    bucket_url = self.bucket.url()

    logger.info('Spinning up instances...', queue=self.deployment_uid)

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
      return

    logger.info('Validating cluster (this could take awhile)...', queue=self.deployment_uid)

    # Wait until our cluster is up and running
    self.validate_cluster(bucket_url)

    # Make an API deploy once cluster is validated (if desired)
    if self.with_deploy:
      logger.info('Scheduling deploy to API cluster...', queue=self.deployment_uid, section=True)
      sleep(5)

      api_deployer = ApiDeploy(deployment_uid=self.deployment_uid)
      job_queue.add(api_deployer.deploy, meta={'deployment': self.deployment_uid})

  def validate_cluster(self, state):
    while not kops.validate_cluster(name=self.cluster.name, state=state):
      logger.info('Pinging cluster until response...', queue=self.deployment_uid)
      sleep(120)

    # Register that the cluster is validated
    logger.info('Cluster successfully created.', queue=self.deployment_uid)

    dbi.update(self.cluster, {'validated': True})

  def set_db_reliant_attrs(self):
    self.team = dbi.find_one(Team, {'uid': self.team_uid})
    self.cluster = self.team.cluster
    self.bucket = self.cluster.bucket