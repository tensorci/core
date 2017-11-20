from src.statuses.pred_statuses import pstatus
from post_train_building import PostTrainBuilding
from post_training import PostTraining
from post_api_building import PostApiBuilding

# populate these with services accordingly
status_update_services = {
  pstatus.DONE_BUILDING_FOR_TRAIN: PostTrainBuilding,
  pstatus.DONE_TRAINING: PostTraining,
  pstatus.DONE_BUILDING_FOR_API: PostApiBuilding
}