import os
import boto3
import re
from src import logger
from uuid import uuid4

os_map = {
  'ubuntu-16.04': '099720109477/ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-20171026.1'
}


def create_s3_bucket(name):
  logger.info('Creating S3 Bucket: {}...'.format(name))

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
  logger.info('Creating Route53 Hosted Zone: {}...'.format(name))
  hosted_zone_id = None
  hosted_zone = None
  name_servers = None

  try:
    route53 = boto3.client('route53')
    hosted_zones = [hz for hz in route53.list_hosted_zones().get('HostedZones')]

    for hz in hosted_zones:
      # If hosted zone already exists, get name_servers for it
      if hz.get('Name') == '{}.'.format(name):
        hosted_zone_id = re.match('/hostedzone/([0-9A-Za-z]+)', hz.get('Id')).groups()[0]
        hosted_zone = route53.get_hosted_zone(Id=hosted_zone_id)
        break

    if not hosted_zone:
      hosted_zone = route53.create_hosted_zone(Name=name, CallerReference=uuid4().hex)
      hosted_zone_id = re.match('/hostedzone/([0-9A-Za-z]+)',
                                hosted_zone.get('HostedZone', {}).get('Id')).groups()[0]

    name_servers = hosted_zone.get('DelegationSet', {}).get('NameServers') or []
  except BaseException as e:
    logger.error('Error Creating Route 53 Hosted Zone (name={}) with error: {}'.format(name, e))

  return hosted_zone_id, name_servers


def add_dns_records(hosted_zone_id, domain, records, type):
  logger.info('Adding {} DNS record(s) to {}...'.format(type, domain))

  changes = [{
    'Action': 'UPSERT',
    'ResourceRecordSet': {
      'Name': domain,
      'Type': type,
      'TTL': 60,
      'ResourceRecords': [{'Value': r} for r in records]
    }
  }]

  try:
    route53 = boto3.client('route53')

    route53.change_resource_record_sets(
      HostedZoneId=hosted_zone_id,
      ChangeBatch={'Changes': changes}
    )
  except BaseException as e:
    logger.error('Error Adding DNS records to hosted_zone_id({}) with error: {}'.format(hosted_zone_id, e))
    return False

  return True