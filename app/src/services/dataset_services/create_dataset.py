import json
from src import logger, dbi
from src.models import Dataset
from src.utils import dataset_db


class CreateDataset(object):

  def __init__(self, name, prediction=None, fileobj=None):
    self.name = name
    self.prediction = prediction
    self.fileobj = fileobj

  def perform(self):
    # Create Dataset record in core DB
    dataset = dbi.create(Dataset, {
      'prediction': self.prediction,
      'name': self.name
    })

    # Parse the JSON dataset
    data = json.loads(self.fileobj.read())

    # Blow up if data isn't an array -- the required format
    if type(data) != list:
      raise BaseException('Data is not a JSON array')

    prediction_slug = self.prediction.slug.replace('-', '_')
    dataset_slug = dataset.slug.replace('-', '_')

    # Create a new table in our dataset DB for the dataset's records
    table_name = '{}_{}'.format(prediction_slug, dataset_slug)
    dataset_db.create_table(table_name)

    # Batch insert the data into the table
    dataset_db.populate_records(data, table=table_name)