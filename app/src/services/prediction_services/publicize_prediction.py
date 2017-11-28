import os
from src import dbi, aplogger
from src.utils.aws import add_dns_records
from time import sleep
from kubernetes import client, config


class PublicizePrediction(object):

  def __init__(self, prediction=None, port=80, target_port=80):
    self.prediction = prediction
    self.port = port
    self.target_port = target_port
    self.team = self.prediction.team
    self.cluster = self.team.cluster.name
    self.deploy_name = self.prediction.deploy_name
    self.service_name = self.deploy_name
    self.config = config
    self.client = client

  def perform(self):
    # Switch to appropriate kubectl context
    os.system('kubectl config use-context {}'.format(self.cluster))

    # Expose deployment with a LoadBalancer service
    # TODO: Figure out how to do all of this with the kubernetes python client we're already using
    os.system('kubectl expose deployment/{} --type=LoadBalancer --port={} --target-port={} --name={}'.format(
      self.deploy_name, self.port, self.target_port, self.service_name))

    # Probs don't need to do this again if already doing it above but doing again
    # just to be sure in case CLI and py version differ
    self.config.load_kube_config(context=self.cluster)

    # Get ELB for service
    elb_url = self.wait_for_elb()

    # Update the prediction record with the ELB's url
    self.prediction = dbi.update(self.prediction, {'elb': elb_url})

    # Create a CNAME record for your subdomain with the ELB's url
    add_dns_records(os.environ.get('TL_HOSTED_ZONE_ID'), self.prediction.domain, [elb_url], 'CNAME')

    aplogger.info('Prediction live at {}/api/predict'.format(self.prediction.domain))

  def wait_for_elb(self):
    elb = self.get_elb()

    if not elb:
      sleep(5)
      return self.wait_for_elb()

    return elb

  def get_elb(self, api):
    try:
      service_list = api.list_namespaced_service(namespace='default',
                                                 label_selector='app={}'.format(self.deploy_name))

      items = service_list.items or []
    except:
      return None

    if not items:
      return None

    service = items[0]

    try: # me being lazy
      elb = service.status.load_balancer.ingress[0].hostname
    except:
      return None

    return elb