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
  # TODO: Make this valid SQL
  conn.execute('CREATE TABLE records (data: json)')