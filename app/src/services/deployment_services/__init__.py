from src.models import Deployment
from done_training import DoneTraining

statuses = Deployment.statuses

deployment_status_update_svcs = {
  statuses.DONE_TRAINING: DoneTraining
}