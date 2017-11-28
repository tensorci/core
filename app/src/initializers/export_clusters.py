import os
from src import dbi
from src.models import Cluster
from src.utils.kops import export_cluster


def perform():
  if os.environ.get('FORCE_CLUSTER_REFRESH') or not os.path.exists(os.environ.get('KUBECONFIG')):
    # Export train cluster
    train_cluster_name = os.environ.get('TRAIN_CLUSTER_NAME')
    train_cluster_state = os.environ.get('TRAIN_CLUSTER_STATE')

    if train_cluster_name and train_cluster_state:
      export_cluster(name=train_cluster_name, state=train_cluster_state)

    # Export build server cluster
    bs_cluster_name = os.environ.get('BS_CLUSTER_NAME')
    bs_cluster_state = os.environ.get('BS_CLUSTER_STATE')

    if bs_cluster_name and bs_cluster_state:
      export_cluster(name=bs_cluster_name, state=bs_cluster_state)

    # Export API clusters
    for cluster in dbi.find_all(Cluster, {'validated': True}):
      bucket = cluster.bucket

      if bucket and bucket.name:
        export_cluster(name=cluster.name, state=bucket.url())