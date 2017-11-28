from logging import StreamHandler, FileHandler, INFO
import sys
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import get_config
from helpers.env import is_prod

# Create and configure the Flask app
app = Flask(__name__)
app.config.from_object(get_config())

# Set up logging
if is_prod():
  app.logger.addHandler(StreamHandler(sys.stdout))
else:
  app.logger.addHandler(FileHandler('main.log'))

app.logger.setLevel(INFO)
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
from initializers import export_clusters
export_clusters.perform()