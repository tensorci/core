from operator import attrgetter


def formatted_graphs(graphs):
  resp = []

  for graph in sorted(graphs, key=attrgetter('created_at'), reverse=True):
    formatted_graph = {
      'uid': graph.uid,
      'title': graph.title,
      'x_axis': graph.x_axis,
      'y_axis': graph.y_axis,
      'data_groups': []
    }

    for group in sorted(graph.graph_data_groups, key=attrgetter('created_at'), reverse=True):
      data = [data_point.data for data_point in group.graph_data_points]
      data.sort(key=lambda d: d['x'])

      formatted_group = {
        'name': group.name,
        'color': group.color,
        'data': data
      }

      formatted_graph['data_groups'].append(formatted_group)

    resp.append(formatted_graph)

  return resp