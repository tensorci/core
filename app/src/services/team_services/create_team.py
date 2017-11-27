from src import dbi
from src.models import Team, TeamUser, Cluster, Bucket


class CreateTeam(object):

  def __init__(self, name=None, owner=None):
    self.name = name
    self.owner = owner

  def perform(self):
    # Create new team
    team = dbi.create(Team, {'name': self.name})

    # Create a new TeamUser to be owner of this team
    dbi.create(TeamUser, {
      'team': team,
      'user': self.owner,
      'role': TeamUser.roles.OWNER
    })

    # Create the Cluster model for this team
    cluster = dbi.create(Cluster, {'team': team})

    # Create the Bucket model for this cluster
    dbi.create(Bucket, {'cluster': cluster})