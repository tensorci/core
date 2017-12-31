from src import dbi
from src.models import Team, Cluster, Bucket


class CreateTeam(object):

  def __init__(self, name=None, provider=None):
    self.name = name
    self.provider = provider
    self.team = None
    self.cluster = None
    self.bucket = None

  def perform(self):
    # Create new team
    self.team = dbi.create(Team, {'name': self.name, 'provider': self.provider})

    # Create the Cluster model for this team
    self.cluster = dbi.create(Cluster, {'team': self.team})

    # Create the Bucket model for this cluster
    self.bucket = dbi.create(Bucket, {'cluster': self.cluster})