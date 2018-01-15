from src.utils.kops import export_cluster
from kubernetes import config


class ExportCluster(object):

  def __init__(self, cluster=None):
    self.cluster = cluster

  def perform(self):
    # Export cluster if not already exported
    if not self.already_exported():
      export_cluster(name=self.cluster.name, state=self.cluster.bucket.url())

  def already_exported(self):
    existing_contexts = config.list_kube_config_contexts()

    if not existing_contexts:
      return False

    return self.cluster.name in [ctx.get('name') for ctx in existing_contexts[0]]