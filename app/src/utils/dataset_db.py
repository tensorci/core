import os
from sqlalchemy import create_engine

dataset_db_url = os.environ.get('DATASET_DB_URL')

if dataset_db_url:
  engine = create_engine(dataset_db_url)
else:
  print('DATASET_DB_URL env not set. Not creating SQLAlchemy engine.')


def get_conn():
  return engine.connect()


def create_table(name):
  conn = get_conn()
  # Create a table named <name> with a json column named 'data'


def populate_records(records, table=None):
  # Do a batch insert to <table> with data=record for each record in records
  pass