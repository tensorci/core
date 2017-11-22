import logging
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import get_config
from helpers.env import is_prod
import logging

# Create and configure the Flask app
app = Flask(__name__)
app.config.from_object(get_config())

# Get ref to logger
logging.basicConfig()
app.logger.setLevel(logging.INFO)
logger = app.logger

# Create and start our delayed job scheduler
from scheduler import delayed
delayed.start()

# Set up Postgres DB
db = SQLAlchemy(app)

# Set up API routes
from routes import api
api.init_app(app)

# Require SSL if on prod
if is_prod() and os.environ.get('REQUIRE_SSL') == 'true':
  from flask_sslify import SSLify
  SSLify(app)

# Execute any startup scripts here
# Export all cluster's configs here (train cluster + all teams' clusters)
# os.system('kops export kubecfg emirates.glimpse.ai --state s3://glimpse-ai')
# os.system('cat $HOME/.kube/config')