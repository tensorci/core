from flask import request
from flask_restplus import Resource
from src.routes import namespace, api
from src.models import Prediction, Dataset
from src import logger, dbi
from src.helpers.user_helper import current_user
from src.api_responses.errors import *
from src.api_responses.success import *


@namespace.route('/dataset')
class RestfulDataset(Resource):
  """Restful interface for the Dataset model"""

  @namespace.doc('create_dataset')
  def post(self):
    # Get current user
    user = current_user()

    if not user:
      return UNAUTHORIZED

    # Get refs to payload info
    payload = dict(request.form.items())
    team_slug = payload.get('team_slug')
    prediction_slug = payload.get('prediction_slug')
    dataset_slug = payload.get('dataset_slug')

    if not team_slug or not prediction_slug or not dataset_slug:
      return INVALID_INPUT_PAYLOAD

    files = dict(request.files.items()) or {}
    f = files.get('file')

    if not f:
      return NO_FILE_PROVIDED

    stream = f.stream

    # Find a team for the provided team_slug that belongs to this user
    team = user.team_for_slug(team_slug)

    if not team:
      return TEAM_NOT_FOUND

    # Find prediction for provided slug and team
    prediction = dbi.find_one(Prediction, {'slug': prediction_slug, 'team': team})

    if not prediction:
      return PREDICTION_NOT_FOUND

    dataset = dbi.find_one(Dataset, {'slug': dataset_slug, 'prediction': prediction})

    if dataset:
      return DATASET_NAME_TAKEN

    try:
      dataset = dbi.create(Dataset, {
        'prediction': prediction,
        'name': dataset_slug
      })
    except BaseException as e:
      logger.error('Error creating Dataset(name={}, prediction={}): {}'.format(dataset_slug, prediction, e))
      return DATASET_CREATION_FAILED

    # TODO: add all the uploading logic here

    return DATASET_CREATION_SUCCESS