class DeploymentStatuses:
  CREATED = 'created'
  TRAIN_BUILD_SCHEDULED = 'train_build_scheduled'
  BUILDING_FOR_TRAIN = 'train_building'
  DONE_BUILDING_FOR_TRAIN = 'train_building_done'
  TRAINING_SCHEDULED = 'training_scheduled'
  TRAINING = 'training'
  DONE_TRAINING = 'training_done'
  API_BUILD_SCHEDULED = 'api_build_scheduled'
  BUILDING_FOR_API = 'api_building'
  DONE_BUILDING_FOR_API = 'api_building_done'
  PREDICTING_SCHEDULED = 'predicting_scheduled'
  PREDICTING = 'predicting'

  def __init__(self):
    self.statuses = [
      self.CREATED,
      self.TRAIN_BUILD_SCHEDULED,
      self.BUILDING_FOR_TRAIN,
      self.DONE_BUILDING_FOR_TRAIN,
      self.TRAINING_SCHEDULED,
      self.TRAINING,
      self.DONE_TRAINING,
      self.API_BUILD_SCHEDULED,
      self.BUILDING_FOR_API,
      self.DONE_BUILDING_FOR_API,
      self.PREDICTING_SCHEDULED,
      self.PREDICTING
    ]


ds = DeploymentStatuses()