import os


def perform():
  if not os.path.exists(os.environ.get('KUBECONFIG')):
    os.system('kops export kubecfg emirates.glimpse.ai --state s3://glimpse-ai')