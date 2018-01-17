from src import dbi, logger
from src.models import Deployment
from src.utils import clusters
from src.deploys.build_server_deploy import BuildServerDeploy
from src.deploys.train_deploy import TrainDeploy
from src.utils.job_queue import job_queue


class RetrainModel(object):

  def __init__(self, repo=None, latest_deployment=None, dataset=None, curr_record_count=None):
    self.repo = repo
    self.latest_deployment = latest_deployment
    self.commit = self.latest_deployment.commit
    self.dataset = dataset
    self.curr_record_count = curr_record_count
    self.triggered_by = 'TensorCI'  # auto-triggered

  def perform(self):
    # Create new deployment with the same commit as the latest deployment.
    new_deployment = dbi.create(Deployment, {
      'repo': self.repo,
      'commit': self.commit,
      'train_triggered_by': self.triggered_by,
      'intent': Deployment.intents.TRAIN
    })

    # Get proper deployer class, based on if SHA has already been built.
    deployer = self.get_deployer(new_deployment)

    # Schedule deploy
    job_queue.add(deployer.deploy, meta={'deployment': new_deployment.uid})

    # Update the dataset with it's new current record count
    dbi.update(self.dataset, {'last_train_record_count': self.curr_record_count})

  def get_deployer(self, deployment):
    dstatuses = deployment.statuses

    # If the latest deployment hasn't already uploaded a build for this SHA, schedule a training build.
    if self.latest_deployment.status_less_than(dstatuses.DONE_BUILDING_FOR_TRAIN):
      deployer = BuildServerDeploy(deployment_uid=deployment.uid,
                                   build_for=clusters.TRAIN,
                                   update_prediction_model=True)

      status_update = dstatuses.TRAIN_BUILD_SCHEDULED
    else:
      # A build for this SHA has already been uploaded, so just schedule a training cluster deploy.
      deployer = TrainDeploy(deployment_uid=deployment.uid,
                             update_prediction_model=True)

      status_update = dstatuses.TRAINING_SCHEDULED

    # Apply the appropriate deployment status
    dbi.update(deployment, {'status': status_update})

    # Return the deployer class to be scheduled
    return deployer