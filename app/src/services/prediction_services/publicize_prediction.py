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
    records = [
      {
        'domain': self.prediction.domain,
        'type': 'CNAME',
        'record': elb
      }
    ]

    add_dns_records(self.prediction.hosted_zone_id, records)

    # Validate that it works after a host sec with a simple request