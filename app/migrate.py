"""
Not currently in use, but will be helpful once you figure out when you wanna call this.
"""
from src import db
import os

if __name__ == '__main__':
  db.engine.execute('DROP TABLE IF EXISTS alembic_version;')
  os.system('python manage db init && python manage db migrate && python manage db upgrade')