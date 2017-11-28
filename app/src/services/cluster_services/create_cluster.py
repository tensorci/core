import os
from src import dbi, aplogger
from src.models import Team, Cluster
from src.deploys.api_deploy import ApiDeploy
from src.utils.aws import create_route53_hosted_zone, add_dns_records, os_map
from src.utils import kops
from time import sleep
from src.deploys import create_deploy


class CreateCluster(object):

  def __init__(self, team_uid=None, prediction_uid=None, with_deploy=False):
    self.team_uid = team_uid
    self.team = dbi.find_one(Team, {'uid': team_uid})
    self.cluster = self.team.cluster
    self.bucket = self.cluster.bucket
    self.prediction_uid = prediction_uid
    self.with_deploy = with_deploy

  def perform(self):
    # Create Route53 hosted zone for cluster
    hosted_zone_id, ns_addresses = create_route53_hosted_zone(self.cluster.name)

    # Update the cluster with the Route53 info
    self.cluster = dbi.update(self.cluster, {
      'hosted_zone_id': hosted_zone_id,
      'ns_addresses': ns_addresses
    })

    # Register NS records for each of the ns_addresses with the TLD
    add_dns_records(os.environ.get('TL_HOSTED_ZONE_ID'), self.cluster.name, ns_addresses, 'NS')

    aplogger.info('Waiting 60s for NS records to take effect...')
    sleep(60)

    bucket_url = self.bucket.url()

    # Create cluster with kops name=cluster.name
    kops.create_cluster(
      name=self.cluster.name,
      zones=','.join(self.cluster.zones),
      master_size=self.cluster.master_type,
      node_size=self.cluster.node_type,
      node_count=3, # TODO: put this somewhere as a constant
      state=bucket_url,
      image=os_map.get(self.cluster.image),
      labels='team={}'.format(self.team.slug)
    )

    # Validate the cluster every 30s until it's validated
    # TODO: Instead - use equivalent of k get nodes -l key=val to watch for this cluster being ready
    while not kops.validate_cluster(name=self.cluster.name, state=bucket_url):
      aplogger.info('Validating cluster {}...'.format(self.cluster.name))
      sleep(30)

    # Register that the cluster is validated
    aplogger.info('Validated cluster.')
    dbi.update(self.cluster, {'validated': True})

    # Make an API deploy once cluster is validated (if desired)
    if self.with_deploy:
      aplogger.info('Scheduling API deploy...')
      create_deploy(ApiDeploy, {'prediction_uid': self.prediction_uid})