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


def set_envs(deployment_name=None, envs=None, context=None, cluster=None):
  envs = envs or []

  if not envs:
    return True

  formatted_envs = ['='.join([env.name, env.value]) for env in envs]

  command = ['kubectl', 'set', 'env', 'deployment/{}'.format(deployment_name)] + \
            formatted_envs + \
            ['--context', context, '--cluster', cluster]

  return bool_response_cmd(command)


def remove_envs(deployment_name=None, env_names=None, context=None, cluster=None):
  env_names = env_names or []

  if not env_names:
    return True

  formatted_envs = ['{}-'.format(name) for name in env_names]

  command = ['kubectl', 'set', 'env', 'deployment/{}'.format(deployment_name)] + \
            formatted_envs + \
            ['--context', context, '--cluster', cluster]

  return bool_response_cmd(command)
