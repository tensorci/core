import os
from src import dbi
from src.utils import clusters
from src.utils.aws import add_dns_records
from subprocess import check_output


class PublicizePrediction(object):

  def __init__(self, prediction=None, port=80, target_port=80):
    self.prediction = prediction
    self.port = port
    self.target_port = target_port
    self.team = self.prediction.team
    self.cluster = self.team.cluster.name
    self.deploy_name = '{}-{}'.format(self.prediction.slug, clusters.API)
    self.service_name = self.deploy_name

  # HACK
  # TODO: Figure out how to do all of this with the kubernetes python client we're
  # already using for deploys. There's dog-shit documentation for exposing a deploy with a service
  # and it seems it'll take having to do the ELB creation manually, which sucks.
  def perform(self):
    # Switch to appropriate kubectl context
    os.system('kubectl config use-context {}'.format(self.cluster))

    # Expose deployment with a LoadBalancer service
    os.system('kubectl expose deployment/{} --type=LoadBalancer --port={} --target-port={} --name={}'.format(
      self.deploy_name, self.port, self.target_port, self.service_name))

    # Get the load balancer url
    desc = check_output('kubectl describe service {}'.format(self.service_name).split())
    lines = desc.split('\n')
    elb_line = [l for l in lines if l.startswith('LoadBalancer Ingress')]

    if not elb_line:
      print('No LoadBalancer Ingress info found when describing service {} with context {}'.format(
        self.service_name, self.cluster))
      return

    elb_url = elb_line[0].replace('LoadBalancer Ingress:', '').replace(' ', '')

    # Update the prediction record with the ELB's url
    self.prediction = dbi.update(self.prediction, {'elb': elb_url})

    # Create a CNAME record for your subdomain with the ELB's url
    add_dns_records(os.environ.get('TL_HOSTED_ZONE_ID'),
                    self.prediction.domain,
                    [elb_url],
                    'CNAME')