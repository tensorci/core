class PredictionStatus:
  CREATED = 'created'
  BUILDING_FOR_TRAIN = 'train_building'
  DONE_BUILDING_FOR_TRAIN = 'train_building_done'
  TRAINING = 'training'
  DONE_TRAINING = 'training_done'
  BUILDING_FOR_API = 'api_building'
  DONE_BUILDING_FOR_API = 'api_building_done'
  PREDICTING = 'predicting'

  def __init__(self):
    self.statuses = [
      self.CREATED,
      self.BUILDING_FOR_TRAIN,
      self.DONE_BUILDING_FOR_TRAIN,
      self.TRAINING,
      self.DONE_TRAINING,
      self.BUILDING_FOR_API,
      self.DONE_BUILDING_FOR_API,
      self.PREDICTING
    ]

  def proceeds(self, a, b):
    return self.statuses.index(b) == self.statuses.index(a) + 1

pstatus = PredictionStatus()