from src import db
import os

db.engine.execute('DROP TABLE IF EXISTS alembic_version;')

os.system('python manage db init && python manage db migrate && python manage db upgrade')