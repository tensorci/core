import os
import boto3
from src import logger


def create_s3_bucket(name):
  try:
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(name)

    bucket.create(
      CreateBucketConfiguration={
        'LocationConstraint': os.environ.get('AWS_REGION_NAME')
      })
  except BaseException as e:
    logger.error('Error Creating S3 Bucket (name={}) with error: {}'.format(name, e))
    return False

  return True