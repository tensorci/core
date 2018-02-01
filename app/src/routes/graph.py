import os
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
from src.helpers.definitions import train_cluster_header_name

create_graph_model = api.model('Graph', {
  'deployment_uid': fields.String(required=True),
  'title': fields.String(required=True),
  'x_axis': fields.String(required=True),
  'y_axis': fields.String(required=True)
})


@namespace.route('/graphs')
class RestfulEnvs(Resource):
  """Restful interface for Graphs"""

  @namespace.doc('get_graphs_for_deployment')
  def get(self):
    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    args = dict(request.args.items())
    deployment_uid = args.get('deployment_uid')

    if not deployment_uid:
      logger.error('No deployment_uid provided when fetching graphs for deployment.')
      return INVALID_INPUT_PAYLOAD

    deployment = db.session.query(Deployment).options(
      joinedload(Deployment.graphs)
      .subqueryload(Graph.graph_data_groups)
      .subqueryload(GraphDataGroup.graph_data_points)).filter(Deployment.uid == deployment_uid).first()

    if not deployment:
      logger.error('No deployment found for uid: {}'.format(deployment_uid))
      return DEPLOYMENT_NOT_FOUND

    graphs = formatted_graphs(deployment.graphs)

    return {'graphs': graphs}


@namespace.route('/graph')
class RestfulEnvs(Resource):
  """Restful interface for a Graph"""

  @namespace.doc('create_graph_for_deployment')
  @namespace.expect(create_graph_model, validate=True)
  def post(self):
    if request.headers.get(train_cluster_header_name) != os.environ.get('TENSORCI_TRAIN_SECRET'):
      return UNAUTHORIZED

    provider_user = current_provider_user()

    if not provider_user:
      return UNAUTHORIZED

    payload = api.payload or {}
    deployment_uid = payload['deployment_uid']
    title = payload['title']
    x_axis = payload['x_axis']
    y_axis = payload['y_axis']

    deployment = dbi.find_one(Deployment, {'uid': deployment_uid})

    if not deployment:
      logger.error('No deployment found for uid: {}'.format(deployment_uid))
      return DEPLOYMENT_NOT_FOUND

    graph = dbi.upsert(Graph, {
      'deployment': deployment,
      'title': title
    })

    graph = dbi.update(graph, {
      'x_axis': x_axis,
      'y_axis': y_axis
    })

    return {'uid': graph.uid}