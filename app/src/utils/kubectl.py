from cmd import bool_response_cmd


def expose(resource=None, type='LoadBalancer', port=80, target_port=80, name=None, context=None, cluster=None):

  return bool_response_cmd(['kubectl', 'expose', resource,
                            '--type', type,
                            '--port', str(port),
                            '--target-port', str(target_port),
                            '--name', name,
                            '--context', context,
                            '--cluster', cluster])


def annotate(resource=None, resource_name=None, labels=None, context=None, cluster=None):
  labels = labels or {}
  formatted_labels = ['='.join([str(k), str(v)]) for k, v in labels.items()]

  command = ['kubectl', 'annotate', resource, resource_name] + \
            formatted_labels + \
            ['--context', context, '--cluster', cluster]

  return bool_response_cmd(command)


def set_envs(deployment_name=None, updates=None, removals=None, context=None, cluster=None):
  updates = updates or {}
  removals = removals or []

  if not updates and not removals:
    return True

  # Just double check you won't be removing any envs also in the updates map
  removals = [name for name in removals if name not in updates]

  envs = []

  # First add the updates...
  for name, value in updates.iteritems():
    envs.append('{}={}'.format(name, value))

  # Then add any removals...
  for name in removals:
    envs.append('{}-'.format(name))

  command = ['kubectl', 'set', 'env', 'deployment/{}'.format(deployment_name)] + \
            envs + \
            ['--context', context, '--cluster', cluster]

  return bool_response_cmd(command)