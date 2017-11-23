import os
from src import dbi
from src.models import Cluster


def perform():
  if os.environ.get('FORCE_CLUSTER_REFRESH') or not os.path.exists(os.environ.get('KUBECONFIG')):
    # Export train cluster
    train_cluster_name = os.environ.get('TRAIN_CLUSTER_NAME')
    train_cluster_state = os.environ.get('TRAIN_CLUSTER_STATE')

    if train_cluster_name and train_cluster_state:
      export_cluster(name=train_cluster_name, state=train_cluster_state)

    # Export API clusters
    clusters = [(c.name, c.state) for c in dbi.find_all(Cluster)]

    for name, state in clusters:
      export_cluster(name=name, state=state)


def export_cluster(name=None, state=None):
  assert not name.startswith('$(')
  assert not state.startswith('$(')
  os.system('kops export kubecfg {} --state {}'.format(name, state))