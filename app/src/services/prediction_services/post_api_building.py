from src import dbi
from src.statuses.pred_statuses import pstatus
from src.deploys import create_deploy
from src.deploys.api_deploy import ApiDeploy
from src.scheduler import delayed, delay_class_method
from src.services.cluster_services.create_cluster import CreateCluster


class PostApiBuilding(object):

  def __init__(self, prediction=None):
    self.prediction = prediction

  def perform(self):
    # Update prediction status
    dbi.update(self.prediction, {'status': pstatus.DONE_BUILDING_FOR_API})

    team = self.prediction.team

    if team.cluster:
      # Deploy to cluster if already exists
      create_deploy(ApiDeploy, {'prediction_uid': self.prediction.uid})
    else:
      # Otherwise, create cluster and then deploy
      delayed.add_job(
        delay_class_method,
        args=[CreateCluster, {
          'team_uid': team.uid,
          'prediction_uid': self.prediction.uid,
          'with_deploy': True
        }])