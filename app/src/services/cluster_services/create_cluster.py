from src import dbi
from src.models import Team, Cluster
from src.deploys.api_deploy import ApiDeploy
from src.utils.aws import create_route53_hosted_zone, add_dns_records, os_map
from src.utils import kops


class CreateCluster(object):

  def __init__(self, team_uid=None, prediction_uid=None, with_deploy=False):
    self.team_uid = team_uid
    self.team = dbi.find_one(Team, {'uid': team_uid})
    self.prediction_uid = prediction_uid
    self.with_deploy = with_deploy

  def perform(self):
    # Create Cluster model for team
    cluster = dbi.create(Cluster, {'team': self.team})

    # Create Route53 hosted zone for cluster (NS Records are also automatically added)
    hosted_zone_id, ns_addresses = create_route53_hosted_zone(cluster.name)

    # Update the cluster with the Route53 info
    cluster = dbi.update(cluster, {
      'hosted_zone_id': hosted_zone_id,
      'ns_addresses': ns_addresses
    })

    # Create cluster with kops name=cluster.name
    kops.create_cluster(
      name=cluster.name,
      zones=','.join(cluster.zones),
      master_size=cluster.master_type,
      node_size=cluster.node_type,
      node_count=3,  # TODO: put this somewhere as a constant
      state=cluster.state,
      image=os_map.get(cluster.image)
    )

    # Validate the cluster...
    # Probably use subprocess.check_output to get the output
    # Do this

    # Make an API deploy post-cluster-validation if desired
    if self.with_deploy:
      deployer = ApiDeploy(prediction_uid=self.prediction_uid)
      deployer.deploy()