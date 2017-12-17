import os
from sqlalchemy import create_engine

dataset_db_url = os.environ.get('DATASET_DB_URL')

if dataset_db_url:
  engine = create_engine(dataset_db_url)
else:
  print('DATASET_DB_URL env not set. Not creating SQLAlchemy engine.')


def create_table(name):
  engine.execute('CREATE TABLE {}(id serial PRIMARY KEY, data JSON);'.format(name))


def populate_records(records, table=None):
  # Add all this shit to the table