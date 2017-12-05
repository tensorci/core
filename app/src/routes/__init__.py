from flask_restplus import Api

api = Api(version='0.1', title='TensorCI Core API')
namespace = api.namespace('api')

# Add all route handlers here:
from team import *
from user import *
from deployment import *