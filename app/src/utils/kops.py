from cmd import bool_response_cmd


def export_cluster(name=None, state=None):
  return bool_response_cmd(['kops', 'export', 'kubecfg', name, '--state', state])


def create_cluster(name=None, zones=None, master_size=None, node_size=None,
                   node_count=None, state=None, image=None, version=None):

  return bool_response_cmd(['kops', 'create', 'cluster',
                            '--name', name,
                            '--zones', zones,
                            '--master-size', master_size,
                            '--node-size', node_size,
                            '--node-count', node_count,
                            '--state', state,
                            '--image', image,
                            '--kubernetes-version', version,
                            '--yes'
                            ])


def validate_cluster(name=None, state=None):
  return bool_response_cmd(['kops', 'validate', 'cluster', '--name', name, '--state', state])