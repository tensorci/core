from src import dbi, logger
from src.models import Integration


class AbstractIntegration(object):

  def __init__(self, prediction_integration=None):
    self.prediction_integration = prediction_integration

    # If prediction_integration provided, get integration and prediction through that
    if prediction_integration:
      self.integration = self.prediction_integration.integration
      self.prediction = self.prediction_integration.prediction
    else:
      # otherwise, manually get integration for the child class's slug
      self.integration = dbi.find_one(Integration, {'slug': self.slug})
      self.prediction = None