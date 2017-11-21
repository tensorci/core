from src import dbi
from src.statuses.pred_statuses import pstatus
from src.deploys import create_deploy
from src.deploys.train_deploy import TrainDeploy
from src.utils.aws import create_s3_bucket


class PostTrainBuilding(object):

  def __int__(self, prediction=None):
    self.prediction = prediction

  def perform(self):
    # Update prediction status
    dbi.update(self.prediction, {'status': pstatus.DONE_BUILDING_FOR_TRAIN})

    team = self.prediction.team

    # If team doesn't have an s3 bucket yet, create that now.
    # We know the S3 hasn't been created yet if the team still doesn't have a cluster
    if not team.cluster:
      bucket_name = 's3://{}'.format(team.slug)
      create_s3_bucket(bucket_name)

    # Schedule a deploy to the training cluster
    create_deploy(TrainDeploy, {'prediction_uid': self.prediction.uid})