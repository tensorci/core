"""
Fix deployments with blank 'intent' and 'intent_updated_at' columns.
"""
from src import dbi
from src.models import Deployment


for dep in dbi.find_all(Deployment):
  updates = {}

  if not dep.intent:
    if dep.status_greater_than(dep.statuses.DONE_TRAINING):
      intent = dep.intents.SERVE
    else:
      intent = dep.intents.TRAIN

    updates['intent'] = intent

  if not dep.intent_updated_at:
    updates['intent_updated_at'] = dep.created_at

  dbi.update(dep, updates)