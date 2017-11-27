from src.statuses.pred_statuses import pstatus
from post_training import PostTraining

status_update_services = {
  pstatus.DONE_TRAINING: PostTraining
}