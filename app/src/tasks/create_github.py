"""
Create GitHub integration
"""
import os
from src import dbi, logger
from src.models import Integration

gh = dbi.find_one(Integration, {'slug': 'github'})

if gh:
  logger.error('github integration already exists. exiting...')
  exit(1)

dbi.create(Integration, {'name': 'GitHub'})