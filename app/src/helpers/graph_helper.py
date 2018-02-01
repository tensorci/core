def formatted_graphs(graphs):
  resp = []

  for graph in graphs:
    formatted_graph = {
      'uid': graph.uid,
      'title': graph.title,
      'x_axis': graph.x_axis,
      'y_axis': graph.y_axis,
      'data_groups': []
    }

    for group in graph.graph_data_groups:
      formatted_group = {
        'name': group.name,
        'color': group.color,
        'data': [data_point.data for data_point in group.graph_data_points]
      }

      formatted_graph['data_groups'].append(formatted_group)

    resp.append(formatted_graph)

  return resp