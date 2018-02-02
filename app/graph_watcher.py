import json
from src.utils.pyredis import redis
from src import dbi, db
from src.models import Graph, GraphDataGroup, GraphDataPoint, Deployment
from src.utils import pubsub
from src.helpers.definitions import graph_update_queue
from src.helpers.graph_helper import formatted_graphs
from sqlalchemy.orm import joinedload


def handle_new_data_point(item):
  item = json.loads(item[1]) or {}

  if not item:
    return

  graph_uid = item.get('graph_uid')
  series = item.get('series') or 'default'
  color = item.get('color')
  x = item.get('x')
  y = item.get('y')

  if not graph_uid or x is None or y is None:
    return

  graph = dbi.find_one(Graph, {'uid': graph_uid})

  if not graph:
    return

  group, is_new = dbi.upsert(GraphDataGroup, {
    'graph': graph,
    'name': series,
  })

  if color:
    dbi.update(group, {'color': color})

  dbi.create(GraphDataPoint, {
    'graph_data_group': group,
    'data': {
      'x': x,
      'y': y
    }
  })

  deployment_id = graph.deployment_id

  deployment = db.session.query(Deployment).options(
    joinedload(Deployment.graphs)
      .subqueryload(Graph.graph_data_groups)
      .subqueryload(GraphDataGroup.graph_data_points)).filter(Deployment.id == deployment_id).first()

  if not deployment:
    return

  payload = {'graphs': formatted_graphs(deployment.graphs)}

  pubsub.publish(channel=graph_uid, data=payload)


def watch():
  while True:
    item = redis.blpop(graph_update_queue, timeout=30)

    if not item:
      continue

    try:
      handle_new_data_point(item)
    except BaseException as e:
      print(e.__dict__)


if __name__ == '__main__':
  watch()