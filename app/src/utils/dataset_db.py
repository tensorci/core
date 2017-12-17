import os
import json
from sqlalchemy import create_engine

dataset_db_url = os.environ.get('DATASET_DB_URL')

if dataset_db_url:
  engine = create_engine(dataset_db_url)
else:
  print('DATASET_DB_URL env not set. Not creating SQLAlchemy engine.')


def create_table(name):
  engine.execute('CREATE TABLE {} (id serial PRIMARY KEY NOT NULL, data json NOT NULL);'.format(name))


def populate_records(records, table=None):
  for r in records:
    engine.execute('INSERT INTO {} (data) VALUES (\'{}\')'.format(table, json.dumps(r)))