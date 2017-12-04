from src import db

if __name__ == '__main__':
  db.engine.execute('DROP TABLE IF EXISTS alembic_version;')