from src import dbi, logger
from src.models import Deployment
from src.utils import clusters
from src.deploys.build_server_deploy import BuildServerDeploy
from src.deploys.train_deploy import TrainDeploy
from src.utils.job_queue import job_queue
from src.helpers.deployment_statuses import ds


class RetrainModel(object):

  def __init__(self, repo=None, latest_deployment=None, dataset=None, curr_record_count=None):
    self.repo = repo
    self.latest_deployment = latest_deployment
    self.dataset = dataset
    self.curr_record_count = curr_record_count

  def perform(self):
    # Create new deployment with the same SHA as the latest deployment.
    new_deployment = dbi.create(Deployment, {
      'repo': self.repo,
      'sha': self.latest_deployment.sha
    })

    # Get proper deployer class, based on if SHA has already been built.
    deployer = self.get_deployer(new_deployment)

    # Schedule deploy
    job_queue.add(deployer.deploy, meta={'deployment': new_deployment.uid})

    # Update the dataset with it's new current record count
    dbi.update(self.dataset, {'last_train_record_count': self.curr_record_count})

  def get_deployer(self, deployment):
    # Schedule a training build if the latest deployment hasn't already uploaded a build for this SHA.
    if ds.statuses.index(self.latest_deployment.status) < ds.statuses.index(ds.DONE_BUILDING_FOR_TRAIN):
      deployer = BuildServerDeploy(deployment_uid=deployment.uid,
                                   build_for=clusters.TRAIN,
                                   update_prediction_model=True)
    else:
      # A build for this SHA has already been uploaded, so just deploy directly to the training cluster
      # and update this deployment's status to DONE_BUILDING_FOR_TRAIN.
      deployment = dbi.update(deployment, {'status': ds.DONE_BUILDING_FOR_TRAIN})
      deployer = TrainDeploy(deployment_uid=deployment.uid, update_prediction_model=True)

    return deployer