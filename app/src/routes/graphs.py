from flask import request
from flask_restplus import Resource, fields
from src.routes import namespace, api
from src import dbi, logger, db
from src.models import Deployment, Graph, GraphDataGroup, GraphDataPoint
from sqlalchemy.orm import joinedload
from src.api_responses.errors import *
from src.api_responses.success import *
from src.helpers.provider_user_helper import current_provider_user
from src.helpers.graph_helper import formatted_graphs


@namespace.route('/graphs')
class RestfulEnvs(Resource):
  """Restful interface for a Graph"""

  @namespace.doc('get_graphs_for_deployment')
  def get(self):
    # provider_user = current_provider_user()
    #
    # if not provider_user:
    #   return UNAUTHORIZED
    #
    # args = dict(request.args.items())
    # deployment_uid = args.get('deployment_uid')
    #
    # if not deployment_uid:
    #   logger.error('No deployment_uid provided when fetching graphs for deployment.')
    #   return INVALID_INPUT_PAYLOAD
    #
    # deployment = db.session.query(Deployment).options(
    #   joinedload(Deployment.graphs)
    #   .subqueryload(Graph.graph_data_groups)
    #   .subqueryload(GraphDataGroup.graph_data_points)).filter(Deployment.uid == deployment_uid).all()
    #
    # if not deployment:
    #   logger.error('No deployment found for uid: {}'.format(deployment_uid))
    #   return DEPLOYMENT_NOT_FOUND
    #
    # graphs = formatted_graphs(deployment.graphs)
    #
    # return {'graphs': graphs}
    return {'graphs': []}