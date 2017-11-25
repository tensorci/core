import os
from src import dbi
from src.utils.aws import add_dns_records


class PublicizePrediction(object):

  def __init__(self, prediction=None):
    self.prediction = prediction

  def perform(self):
    # Expose prediction's deployment with ELB
    # Do this

    # Get the url for your new ELB
    elb = None  # returned from last command

    # Add elb to prediction
    self.prediction = dbi.update(self.prediction, {'elb': elb})

    # Create a CNAME record for your subdomain with the ELB's url
    add_dns_records(os.environ.get('TL_HOSTED_ZONE_ID'), self.prediction.domain, [elb], 'CNAME')

    # Validate that it works after a sec with a simple request