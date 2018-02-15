from logging import StreamHandler, INFO
import sys
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from config import config
from utils.logger import Logger
from utils.sse_broadcaster import SSEBroadcaster

# Create and configure the Flask app
app = Flask(__name__)
app.config.from_object(config)

# Set up our logger
app.logger.addHandler(StreamHandler(sys.stdout))
app.logger.setLevel(INFO)
logger = Logger(app.logger)

# Set up Postgres DB
db = SQLAlchemy(app)

# Set up API routes
from routes import api
api.init_app(app)

# Set up websocket connection and SSE broadcaster
socket = SocketIO(app, binary=True)
SSEBroadcaster(socket)

# Execute any startup scripts here
if os.environ.get('AUTO_EXPORT_CLUSTERS') == 'true':
  from initializers import export_clusters
  export_clusters.perform()