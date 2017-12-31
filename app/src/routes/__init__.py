from flask_restplus import Api

api = Api(version='0.1', title='TensorCI Core API')
namespace = api.namespace('api')

# Add all route handlers here:
from provider_user import *
# from deployment import *
from dataset import *
from gh import *
from repo import *