from src import dbi
from src.models import Team, Cluster
from src.deploys.api_deploy import ApiDeploy
from src.utils.aws import create_route53_hosted_zone, add_dns_records


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

    # Format the ns_addresses for this hosted_zone as NS DNS records
    records = []
    for address in ns_addresses:
      records.append({
        'domain': cluster.name,
        'type': 'NS',
        'record': address
      })

    # Register NS records for each of the ns_addresses
    add_dns_records(hosted_zone_id, records)

    # Create cluster with kops name=cluster.name
    # Do this

    # Validate the cluster...
    # Do this

    if self.with_deploy:
      deployer = ApiDeploy(self.prediction_uid)
      deployer.deploy()