import logging
from logging import StreamHandler, INFO
import sys
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import get_config
from helpers.env import is_prod

# Create and configure the Flask app
app = Flask(__name__)
app.config.from_object(get_config())

# Set up our loggers:

# Use this logger for everything except code running inside a delayed job
app.logger.addHandler(StreamHandler(sys.stdout))
app.logger.setLevel(INFO)
logger = app.logger

# Use this for delayed jobs
aplogger = logging.getLogger('apscheduler.executors.default')
aplogger.setLevel(INFO)
aplogger.addHandler(StreamHandler(sys.stdout))

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
# from initializers import export_clusters
# export_clusters.perform()