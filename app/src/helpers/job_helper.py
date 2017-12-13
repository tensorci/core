from src import dbi, logger
from src.models import Deployment


def handle_job_failure(job, exc_type, exc_value, traceback):
  logger.error("""JOB FAILURE:
  Instance: {}
  Function: {}
  Description: {}
  Meta: {}
  Exception Type: {}
  Exception Value: {}
  """.format(
    job.instance,
    job.func_name,
    job.description,
    job.meta,
    exc_type,
    exc_value))

  meta = job.meta or {}

  # If this job was for a deployment, set the deployment as failed.
  if meta.get('deployment'):
    deployment_uid = meta.get('deployment')
    deployment = dbi.find_one(Deployment, {'uid': deployment_uid})

    if deployment:
      dbi.update(deployment, {'failed': True})
      logger.error('Deployment (sha={}) failed unexpectedly.'.format(deployment.sha), queue=deployment_uid)