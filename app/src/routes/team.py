from flask_restplus import Resource
from src.routes import namespace, api


@namespace.route('/team')
class RestfulTeam(Resource):
  """Restful Team Interface"""

  @namespace.doc('create_new_team')
  def post(self):
    # TODO: Add more things to the DB throughout this function once you've designed DB schema

    # Get user from token

    # Validate user exists

    # Make sure team doesn't already exist for that slug

    # INSERT Team record to DB

    # Create S3 Bucket for this cluster

    # Create Route 53 hosted zone, returning the list of nameserver addresses associated with that zone

    # Register NS records for each of the nameserver addresses returned by last command
    #   domain: <team_slug>-cluster.domain.ai
    #   record: <address>

    # Create cluster with kops with name <team_slug>-cluster.domain.ai

    return '', 201