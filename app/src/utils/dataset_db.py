import os
import json
import psycopg2
from sqlalchemy import create_engine
from StringIO import StringIO

dataset_db_url = os.environ.get('DATASET_DB_URL')

if dataset_db_url:
  engine = create_engine(dataset_db_url)
else:
  print('DATASET_DB_URL env not set. Not creating SQLAlchemy engine.')


def create_table(name):
  engine.execute('CREATE TABLE {} (id serial PRIMARY KEY NOT NULL, data json NOT NULL);'.format(name))


def drop_table(name):
  engine.execute('DROP TABLE {};'.format(name))


def populate_records(records, table=None, sep='|'):
  # Ensure table is empty
  engine.execute('DELETE FROM {};'.format(table))

  # Create a string buffer from all of our records
  i = 0
  data = []
  for r in records:
    i += 1
    data.append('{}{}{}'.format(i, sep, json.dumps(r).replace('\\', '\\\\')))

  buffer = StringIO('\n'.join(data))

  # Get psycopg2 connection and cursor
  conn = psycopg2.connect(os.environ.get('DATASET_DB_URL'))
  cursor = conn.cursor()

  # Bulk insert the records
  cursor.copy_from(buffer, table, sep=sep)
  cursor.commit()


def record_count(table=None):
  result = [r for r in engine.execute('SELECT COUNT(*) FROM {};'.format(table))]

  if not result or not result[0]:
    return 0

  return int(result[0][0])


def sample(table=None, limit=1):
  """
  Get 'count' number of records from a table for preview purposes.
  """
  num_records = record_count(table)

  # If no records in table, return empty list
  if not num_records:
    return []

  result = [r for r in engine.execute('SELECT data FROM {} LIMIT {};'.format(table, limit))]

  if not result:
    return []

  return [r[0] for r in result]