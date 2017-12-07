import os
from src import dbi
from src.models import Cluster
from src.utils.kops import export_cluster
from kubernetes import config


def perform():
  # Contexts map to hold which contexts already exist in our kube config
  existing_contexts = get_existing_contexts()

  # All contexts map
  all_contexts = get_all_contexts()

  # Export missing contexts
  for name, state in all_contexts.iteritems():
    if name not in existing_contexts:
      export_cluster(name=name, state=state)


def get_existing_contexts():
  contexts = {}

  # Make sure our config file exists first before trying to access it
  if os.path.exists(os.environ.get('KUBECONFIG')):
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