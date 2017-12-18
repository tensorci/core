import boto3
from flask import make_response, request
from flask_restplus import Resource
from src.routes import namespace, api
from src.models import Prediction
from src import logger, dbi
from src.helpers.user_helper import current_user
from src.api_responses.errors import *
from src.api_responses.success import *


@namespace.route('/prediction/model')
class FetchModel(Resource):
  """Fetch model file for prediction from S3
  and stream it back to the client"""

  @namespace.doc('fetch_model')
  def get(self):
    # Get current user
    user = current_user()

    if not user:
      return UNAUTHORIZED

    # Parse input args
    args = dict(request.args.items())
    team_slug = args.get('team_slug')
    prediction_slug = args.get('prediction_slug')

    # Find a team for the provided team_slug that belongs to this user
    team = user.team_for_slug(team_slug)

    if not team:
      return TEAM_NOT_FOUND

    # Find prediction for provided slug and team
    prediction = dbi.find_one(Prediction, {'slug': prediction_slug, 'team': team})

    if not prediction:
      return PREDICTION_NOT_FOUND

    # Get the team's S3 bucket
    bucket = team.cluster.bucket

    # Download the file from S3 and stream it back to the client
    s3 = boto3.resource('s3')
    key = prediction.slug + '.ckpt'  # TODO: make this ext storable somewhere

    try:
      file = s3.Object(bucket.name, key).get()
    except BaseException as e:
      logger.error('Error fetching model file from S3 (bucket={}, key={}): {}'.format(bucket.name, key, e))
      return ERROR_PULLING_MODEL_FILE

    resp = make_response(file['Body'].read())

    return resp