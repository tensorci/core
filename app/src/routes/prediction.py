from flask_restplus import Resource
from src.routes import namespace, api


@namespace.route('/prediction')
class RestfulPrediction(Resource):
  """Restful Prediction Interface"""

  @namespace.doc('create_new_prediction_for_team')
  def post(self):
    # Assume input here is github repo
    # List out all the jobs that need to happen when this happens
    return '', 201