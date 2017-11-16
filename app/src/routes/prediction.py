from flask_restplus import Resource
from src.routes import namespace, api


@namespace.route('/prediction')
class RestfulPrediction(Resource):
  """Restful Prediction Interface"""

  @namespace.doc('create_new_prediction_for_team')
  def post(self):
    return '', 201