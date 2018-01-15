import os
from src import db, logger
from sqlalchemy.orm import joinedload
from src.models import Repo
from src.utils.dataset_db import record_count
from src.services.deployment_services.retrain_model import RetrainModel
from time import sleep


def get_repos():
  # Get all repos and eager load datasets
  repos = db.session.query(Repo) \
    .options(joinedload(Repo.datasets)) \
    .filter_by(is_destroyed=False).all()

  logger.info('Found {} repos'.format(len(repos)))

  return repos


def check_if_needs_retrain(repo):
  # Get datasets for repo
  datasets = repo.datasets

  # Repo must have a dataset in order to be retrained
  if not datasets:
    return

  # Get deployments for repo, ordered by most recent
  deployments = repo.ordered_deployments()

  # Repo must have made at least one deployment before being retrained
  if not deployments:
    return

  # Get the latest deployment
  latest_deployment = deployments[0]

  # We're loosely sticking to the 1-dataset-per-repo constraint for now
  dataset = datasets[0]

  # If retrain_step_size hasn't been set, the repo isn't eligible for retraining
  if not dataset.retrain_step_size:
    return

  # Find the current number of records in the dataset table
  table = dataset.table()
  curr_record_count = record_count(table=table)

  # curr_record_count shouldn't ever be falsey (will always be a positive integer)
  if not curr_record_count:
    logger.warn('Current record count returned falsey for table {}'.format(table))
    return

  # Check if it's time to retrain the model based on the number of new records in the dataset
  if (curr_record_count - dataset.last_train_record_count) >= dataset.retrain_step_size:
    logger.info('Time to retrain model for repo, {}. Record count diff: {} --> {}'.format(
      repo.slug, dataset.last_train_record_count, curr_record_count))

    # Retrain the model
    retrain_svc = RetrainModel(repo=repo,
                               latest_deployment=latest_deployment,
                               dataset=dataset,
                               curr_record_count=curr_record_count)
    retrain_svc.perform()


def watch(intv=60):
  while True:
    for repo in get_repos():
      check_if_needs_retrain(repo)

    sleep(intv)


if __name__ == '__main__':
  params = {}

  # Use specified watch interval if specified in env
  if os.environ.get('RETRAIN_WATCH_INTERVAL'):
    params['intv'] = int(os.environ['RETRAIN_WATCH_INTERVAL'])

  watch(**params)