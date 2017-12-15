import os
from src import dbi
from src.models import Cluster
from src.utils.kops import export_cluster
from kubernetes import config


def perform():
  kube_config = os.environ.get('KUBECONFIG')

  # Contexts map to hold which contexts already exist in our kube config
  existing_contexts = get_existing_contexts(kube_config)

  # All contexts map
  all_contexts = get_all_contexts()

  # Find contexts that haven't been exported yet
  missing_contexts = [(name, state) for name, state in all_contexts.items() if name not in existing_contexts]

  # If we need need to export some missing contexts, remove $KUBECONFIG.lock
  if missing_contexts and os.path.exists('{}.lock'.format(kube_config)):
    os.remove('{}.lock'.format(kube_config))

  # Export the missing contexts
  for context in missing_contexts:
    name, state = context
    export_cluster(name=name, state=state)


def get_existing_contexts(kube_config):
  contexts = {}

  # Make sure our config file exists first before trying to access it
  if os.path.exists(kube_config):
    kube_contexts = config.list_kube_config_contexts()

    if kube_contexts and not os.environ.get('FORCE_CLUSTER_REFRESH'):
      contexts = {ctx.get('name'): True for ctx in kube_contexts[0]}

  return contexts


def get_all_contexts():
  contexts = {
    os.environ.get('TRAIN_CLUSTER_NAME'): os.environ.get('TRAIN_CLUSTER_STATE'),
    os.environ.get('BS_CLUSTER_NAME'): os.environ.get('BS_CLUSTER_STATE')
  }

  for c in dbi.find_all(Cluster, {'validated': True}):
    bucket = c.bucket

    if bucket and bucket.name:
      contexts[c.name] = bucket.url()

  return contexts


if __name__ == '__main__':
  perform()