import os
import boto3
import re
from src import logger
from uuid import uuid4

os_map = {
  'ubuntu-16.04': '099720109477/ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-20171026.1'
}


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


def create_route53_hosted_zone(name):
  try:
    route53 = boto3.client('route53')

    resp = route53.create_hosted_zone(
      Name=name,
      CallerReference=uuid4().hex
    )

    hosted_zone_id = resp.get('HostedZone', {}).get('Id')

    if hosted_zone_id:
      match = re.match('/hostedzone/([0-9A-Za-z]+)', hosted_zone_id)

      if match:
        hosted_zone_id = match.groups()[0]

    name_servers = resp.get('DelegationSet', {}).get('NameServers') or []
  except BaseException as e:
    logger.error('Error Creating Route 53 Hosted Zone (name={}) with error: {}'.format(name, e))
    return None

  return hosted_zone_id, name_servers


def add_dns_records(hosted_zone_id, records):
  changes = []

  for zone in records:
    changes.append({
      'Action': 'UPSERT',
      'ResourceRecordSet': {
        'Name': zone.get('domain'),
        'Type': zone.get('type'),
        'TTL': 300,
        'ResourceRecords': [{'Value': zone.get('record')}]
      }
    })

  try:
    route53 = boto3.client('route53')

    route53.change_resource_record_sets(
      HostedZoneId=hosted_zone_id,
      ChangeBatch={'Changes': changes}
    )
  except BaseException as e:
    logger.error('Error Adding DNS records to hosted_zone_id() with error: {}'.format(hosted_zone_id, e))
    return False

  return True