from src import dbi
from src.models import Team, Cluster, Bucket


class CreateTeam(object):

  def __init__(self, name=None, provider=None):
    self.name = name
    self.provider = provider

  def perform(self):
    # Create new team
    team = dbi.create(Team, {'name': self.name, 'provider': self.provider})

    # Create the Cluster model for this team
    cluster = dbi.create(Cluster, {'team': team})

    # Create the Bucket model for this cluster
    dbi.create(Bucket, {'cluster': cluster})