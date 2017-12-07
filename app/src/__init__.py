import logging
from logging import StreamHandler, INFO
import sys
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import get_config

# Create and configure the Flask app
app = Flask(__name__)
app.config.from_object(get_config())

# Set up our logger
app.logger.addHandler(StreamHandler(sys.stdout))
app.logger.setLevel(INFO)
logger = app.logger

# Set up Postgres DB
db = SQLAlchemy(app)

# Set up API routes
from routes import api
api.init_app(app)

# Execute any startup scripts here
if os.environ.get('AUTO_EXPORT_CLUSTERS') == 'true':
  from initializers import export_clusters
  export_clusters.perform()