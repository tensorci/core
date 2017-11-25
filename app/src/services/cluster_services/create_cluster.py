import os
from src import dbi
from src.models import Team, Cluster
from src.deploys.api_deploy import ApiDeploy
from src.utils.aws import create_route53_hosted_zone, add_dns_records, os_map
from src.utils import kops
from time import sleep


class CreateCluster(object):

  def __init__(self, team_uid=None, prediction_uid=None, with_deploy=False):
    self.team_uid = team_uid
    self.team = dbi.find_one(Team, {'uid': team_uid})
    self.prediction_uid = prediction_uid
    self.with_deploy = with_deploy

  def perform(self):
    # Create Cluster model for team
    cluster = dbi.create(Cluster, {'team': self.team})

    # Create Route53 hosted zone for cluster
    hosted_zone_id, ns_addresses = create_route53_hosted_zone(cluster.name)

    # Update the cluster with the Route53 info
    cluster = dbi.update(cluster, {
      'hosted_zone_id': hosted_zone_id,
      'ns_addresses': ns_addresses
    })

    # Prep these addresses as NS records
    records = []
    for address in ns_addresses:
      records.append({
        'domain': cluster.name,
        'type': 'NS',
        'record': address
      })

    # Register NS records for each of the ns_addresses with the TLD
    add_dns_records(os.environ.get('TL_HOSTED_ZONE_ID'), cluster.name, records, 'NS')

    sleep(60)

    # Create cluster with kops name=cluster.name
    kops.create_cluster(
      name=cluster.name,
      zones=','.join(cluster.zones),
      master_size=cluster.master_type,
      node_size=cluster.node_type,
      node_count=3, # TODO: put this somewhere as a constant
      state=cluster.state,
      image=os_map.get(cluster.image)
    )

    # Validate the cluster every 30s until it's validated
    while not kops.validate_cluster(name=cluster.name, state=cluster.state):
      print('Validating cluster {}...'.format(cluster.name))
      sleep(30)

    # Make an API deploy post-cluster-validation
    if self.with_deploy:
      ApiDeploy(prediction_uid=self.prediction_uid).deploy()