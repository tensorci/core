import os
import boto3
from src import logger
from uuid import uuid4


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


# make name <team.slug>-cluster.<config.DOMAIN>
def create_route53_hosted_zone(name):
  name_servers = None

  try:
    route53 = boto3.client('route53')

    resp = route53.create_hosted_zone(
      Name=name,
      CallerReference=uuid4().hex
    )

    name_servers = resp.get('DelegationSet', {}).get('NameServers') or []
  except BaseException as e:
    logger.error('Error Creating Route 53 Hosted Zone (name={}) with error: {}'.format(name, e))

  return name_servers