import os
from src import db, logger, dbi
from sqlalchemy.orm import joinedload
from src.models import Prediction, Deployment
from src.utils.dataset_db import record_count
from src.utils import clusters
from src.deploys.build_server_deploy import BuildServerDeploy
from src.deploys.train_deploy import TrainDeploy
from src.utils.job_queue import job_queue
from time import sleep
from src.helpers.deployment_statuses import ds


def watch(intv=60):
  while True:
    # Get all predictions and eager load datasets
    predictions = db.session.query(Prediction)\
      .options(joinedload(Prediction.datasets))\
      .filter_by(is_destroyed=False).all()

    logger.info('Found {} predictions'.format(len(predictions)))

    for p in predictions:
      datasets = p.datasets

      if not datasets:
        continue

      deployments = p.ordered_deployments()

      if not deployments:
        continue

      latest_deployment = deployments[0]

      # We're loosely sticking to the 1-dataset-per-prediction constraint for now
      dataset = datasets[0]

      if not dataset.retrain_step_size:
        continue

      # Find the current number of records in the dataset table
      table = dataset.table()
      curr_record_count = record_count(table=table)

      if not curr_record_count:
        logger.warn('Current record count returned falsey for table {}'.format(table))
        continue

      # Check if it's time to retrain the model based on the number of new records in the dataset
      if curr_record_count - dataset.last_train_record_count >= dataset.retrain_step_size:
        logger.info('Time to retrain model for prediction, {}.'
                    '\nLast trained with: {} records'
                    '\nNow training with: {} records'.format(p.slug, dataset.last_train_record_count, curr_record_count))

        # Clone the latest deployment
        deployment = dbi.create(Deployment, {
          'prediction': p,
          'sha': latest_deployment.sha
        })

        # Schedule a training build if the latest deployment hasn't already uploaded a build for this SHA.
        if ds.statuses.index(latest_deployment.status) < ds.statuses.index(ds.DONE_BUILDING_FOR_TRAIN):
          deployer = BuildServerDeploy(deployment_uid=deployment.uid,
                                       build_for=clusters.TRAIN,
                                       update_prediction_model=True)
        else:
          # A build for this SHA has already been uploaded, so just deploy directly to the training cluster.
          deployment = dbi.update(deployment, {'status': ds.DONE_BUILDING_FOR_TRAIN})

          deployer = TrainDeploy(deployment_uid=deployment.uid,
                                 update_prediction_model=True)

        # Schedule deploy
        job_queue.add(deployer.deploy, meta={'deployment': deployment.uid})

        # Update the dataset with it's new current record count
        dbi.update(dataset, {'last_train_record_count': curr_record_count})

    sleep(intv)


if __name__ == '__main__':
  params = {}

  # Use specified watch interval if specified in env
  if os.environ.get('RETRAIN_WATCH_INTERVAL'):
    params['intv'] = int(os.environ['RETRAIN_WATCH_INTERVAL'])

  watch(**params)