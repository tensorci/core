from flask_restplus import Api

api = Api(version='0.1', title='TensorCI Core API')
namespace = api.namespace('api')

# Add all route handlers here:
from dataset import *
from deployment import *
from gh import *
from provider_user import *
from repo import *
from user import *
from env import *
from graphs import *