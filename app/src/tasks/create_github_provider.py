"""
Create Github Provider
"""
from src import dbi, logger
from src.models import Provider


github = dbi.find_one(Provider, {'slug': 'github'})

if github:
  logger.error('Provider with slug, "github", already exists. Returning.')
  exit(1)

dbi.create(Provider, {'name': 'Github', 'domain': 'github.com'})