import os
import re
from subprocess import check_output
from aws import os_map


# TODO: add a decorator that validates all args in a function

def export_cluster(name=None, state=None):
  validate_params([name, state])
  os.system('kops export kubecfg {} --state {}'.format(name, state))


def create_cluster(name=None, zones=None, master_size=None, node_size=None,
                   node_count=None, state=None, image=None, labels=None):
  validate_params([name, zones, master_size, node_size, node_count, state, image])
  assert image in os_map.values()

  os.system('kops create cluster --name {} --zones {} --master-size {} --node-size {} --node-count {} --state {} --image {} --cloud-labels {} --yes'.format(
    name, zones, master_size, node_size, node_count, state, image, labels))


def validate_cluster(name=None, state=None):
  validate_params([name, state])
  try:
    output = check_output('kops validate cluster --name {} --state {}'.format(name, state).split())
  except BaseException as e:
    return False

  return output and 'is ready' in output


def validate_params(params):
  for p in params:
    if p is None:
      raise BaseException('Param can\'t be None when using kops')

    if re.match('\$\(.*\)', str(p)):
      raise BaseException('Invalid kops param -- attemped subcommand: {}'.format(p))