"""
Tables:

  Provider
  Team
  Cluster
  Bucket
  Repo
  User
  ProviderUser
  Session
  RepoProviderUser
  Integration
  IntegrationSetting
  Deployment
  TrainJob
  Dataset

Relationships:

  Provider --> has_many --> teams
  Team --> belongs_to --> Provider
  Team --> has_one --> Cluster
  Cluster --> has_one --> Team
  Cluster --> has_one --> Bucket
  Bucket --> has_one --> Cluster
  Team --> has_many --> repos
  Repo --> belongs_to --> Team
  Repo --> has_many --> repo_provider_users
  ProviderUser --> has_many --> repo_provider_users
  RepoProviderUser -- belongs_to --> Repo
  RepoProviderUser -- belongs_to --> ProviderUser
  Provider --> has_many --> provider_users
  User --> has_many --> provider_users
  ProviderUser --> belongs_to --> Provider
  ProviderUser --> belongs_to --> User
  ProviderUser --> has_many --> sessions
  Session --> belongs_to --> ProviderUser
  Repo --> has_one --> Integration
  Integration --> has_one --> Repo
  Integration --> has_one --> IntegrationSetting
  IntegrationSetting --> has_one --> Integration
  Repo --> has_many --> deployments
  Deployment --> belongs_to --> Repo
  Deployment --> has_one --> TrainJob
  TrainJob --> has_one --> Deployment
  Repo --> has_many --> datasets
  Dataset --> belongs_to --> Repo
"""
import datetime
import importlib
from slugify import slugify
from sqlalchemy.dialects.postgresql import JSON
from src import db, dbi, logger
from sqlalchemy.orm import joinedload
from helpers import auth_util, repo_user_roles, instance_types, user_verification_statuses, providers
from helpers.deployment_statuses import ds
from uuid import uuid4
from operator import attrgetter
from config import config


class Provider(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True, nullable=False)
  name = db.Column(db.String(240), nullable=False)
  slug = db.Column(db.String(240), index=True, unique=True, nullable=False)
  domain = db.Column(db.String(240))
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
  is_destroyed = db.Column(db.Boolean, server_default='f')

  providers = providers

  def __init__(self, name=None, domain=None):
    self.uid = uuid4().hex
    self.name = name
    self.slug = slugify(name, separator='-', to_lower=True)
    self.domain = domain

  def __repr__(self):
    return '<Provider id={}, uid={}, name={}, slug={}, domain={}, created_at={}, is_destroyed={}>'.format(
      self.id, self.uid, self.name, self.slug, self.domain, self.created_at, self.is_destroyed)

  def oauth(self):
    oauth_mod = importlib.import_module('src.services.provider_services.oauth.{}_oauth'.format(self.slug))
    klass = getattr(oauth_mod, '{}OAuth'.format(self.name))
    return klass(provider=self)

  def url(self):
    return 'https://' + self.domain

  @staticmethod
  def github():
    return dbi.find_one(Provider, {'slug': providers.GITHUB})


class Team(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True, nullable=False)
  name = db.Column(db.String(240), nullable=False)
  slug = db.Column(db.String(240), index=True, unique=True, nullable=False)
  provider_id = db.Column(db.Integer, db.ForeignKey('provider.id'), index=True, nullable=False)
  provider = db.relationship('Provider', backref='teams')
  cluster = db.relationship('Cluster', uselist=False, back_populates='team')
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, name=None, provider=None, provider_id=None):
    self.uid = uuid4().hex
    self.name = name
    self.slug = slugify(name, separator='-', to_lower=True)

    if provider_id:
      self.provider_id = provider_id
    else:
      self.provider = provider

  def __repr__(self):
    return '<Team id={}, uid={}, name={}, slug={}, provider_id={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.name, self.slug, self.provider_id, self.is_destroyed, self.created_at)


class Cluster(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True, nullable=False)
  team_id = db.Column(db.Integer, db.ForeignKey('team.id'), index=True, nullable=False)
  team = db.relationship('Team', back_populates='cluster')
  bucket = db.relationship('Bucket', uselist=False, back_populates='cluster')
  name = db.Column(db.String(360), nullable=False)
  ns_addresses = db.Column(JSON)
  hosted_zone_id = db.Column(db.String(120))
  zones = db.Column(JSON)
  master_type = db.Column(db.String(120))
  node_type = db.Column(db.String(120))
  image = db.Column(db.String(120))
  validated = db.Column(db.Boolean, server_default='f')
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, team=None, team_id=None, ns_addresses=None, hosted_zone_id=None, zones=None,
               master_type=instance_types.MICRO, node_type=instance_types.MICRO, image='ubuntu-16.04', validated=False):
    self.uid = uuid4().hex

    if team_id:
      self.team_id = team_id
    else:
      self.team = team

    self.team = team
    self.name = '{}-cluster.{}'.format(team.slug, config.DOMAIN)
    self.ns_addresses = ns_addresses or []
    self.hosted_zone_id = hosted_zone_id
    self.zones = zones or ['us-west-1a']  # TODO: Ensure zones are all us-west-1
    self.master_type = master_type
    self.node_type = node_type
    self.image = image
    self.validated = validated

  def __repr__(self):
    return '<Cluster id={}, uid={}, team_id={}, name={}, ns_addresses={}, hosted_zone_id={}, zones={}, master_type={}, ' \
           'node_type={}, image={}, validated={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.team_id, self.name, self.ns_addresses, self.hosted_zone_id, self.zones, self.master_type,
      self.node_type, self.image, self.validated, self.is_destroyed, self.created_at)


class Bucket(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  cluster_id = db.Column(db.Integer, db.ForeignKey('cluster.id'), index=True, nullable=False)
  cluster = db.relationship('Cluster', back_populates='bucket')
  name = db.Column(db.String(240))
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, cluster=None, cluster_id=None, name=None):
    if cluster_id:
      self.cluster_id = cluster_id
    else:
      self.cluster = cluster

    self.name = name

  def __repr__(self):
    return '<Bucket id={}, cluster_id={}, name={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.cluster_id, self.name, self.is_destroyed, self.created_at)

  def url(self):
    if self.name:
      return 's3://' + self.name

    return None


class Repo(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True, nullable=False)
  team_id = db.Column(db.Integer, db.ForeignKey('team.id'), index=True, nullable=False)
  team = db.relationship('Team', backref='repos')
  slug = db.Column(db.String(240), index=True)
  elb = db.Column(db.String(240))
  domain = db.Column(db.String(360))
  image_repo_owner = db.Column(db.String(120))
  deploy_name = db.Column(db.String(360))
  client_id = db.Column(db.String(240))
  client_secret = db.Column(db.String(240))
  model_ext = db.Column(db.String(60))
  internal_msg_token = db.Column(db.String(240))
  integration = db.relationship('Integration', uselist=False, back_populates='repo')
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, team=None, team_id=None, slug=None, elb=None, domain=None, image_repo_owner=None,
               deploy_name=None, client_id=None, client_secret=None, model_ext=None, internal_msg_token=None):
    self.uid = uuid4().hex

    if team_id:
      self.team_id = team_id
    else:
      self.team = team

    self.slug = slug
    self.elb = elb
    # TODO -- come up with a unique domain format that works across providers
    self.domain = domain or '{}.{}'.format(self.slug, config.DOMAIN)
    self.image_repo_owner = image_repo_owner or config.IMAGE_REPO_OWNER
    self.deploy_name = deploy_name
    self.client_id = client_id or uuid4().hex
    self.client_secret = client_secret or auth_util.fresh_secret()
    self.model_ext = model_ext
    self.internal_msg_token = internal_msg_token or auth_util.fresh_secret()

  def __repr__(self):
    return '<Repo id={}, uid={}, team_id={}, slug={}, elb={}, domain={}, ' \
           'image_repo_owner={}, deploy_name={}, model_ext={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.team_id, self.slug, self.elb, self.domain,
      self.image_repo_owner, self.deploy_name, self.model_ext, self.is_destroyed, self.created_at)

  def ordered_deployments(self):
    # TODO: optimize this by order-ing in the actual query
    return sorted(self.deployments, key=attrgetter('created_at'), reverse=True)

  def model_file(self):
    if not self.model_ext:
      return None

    return '{}.{}'.format(self.slug, self.model_ext)

  def api_url(self):
    return 'https://{}/api'.format(self.domain)


class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True, nullable=False)
  email = db.Column(db.String(120), index=True, unique=True)
  hashed_pw = db.Column(db.String(240))
  verification_status = db.Column(db.Integer, nullable=False)
  verification_secret = db.Column(db.String(64))
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  ver_statuses = user_verification_statuses

  def __init__(self, email=None, hashed_pw=None, verification_status=user_verification_statuses.NOT_CONTACTED):
    self.uid = uuid4().hex
    self.email = email
    self.hashed_pw = hashed_pw
    self.verification_status = verification_status
    self.verification_secret = auth_util.fresh_secret()

  def __repr__(self):
    return '<User id={}, uid={}, email={}, hashed_pw={}, verification_status={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.email, self.hashed_pw, self.verification_status, self.is_destroyed, self.created_at)


class ProviderUser(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True, nullable=False)
  provider_id = db.Column(db.Integer, db.ForeignKey('provider.id'), index=True, nullable=False)
  provider = db.relationship('Provider', backref='provider_users')
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True, nullable=False)
  user = db.relationship('User', backref='provider_users')
  username = db.Column(db.String(120), index=True, unique=True)
  access_token = db.Column(db.String(240))
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, provider=None, provider_id=None, user=None, user_id=None, username=None, access_token=None):
    self.uid = uuid4().hex

    if provider_id:
      self.provider_id = provider_id
    else:
      self.provider = provider

    if user_id:
      self.user_id = user_id
    else:
      self.user = user

    self.username = username
    self.access_token = access_token

  def __repr__(self):
    return '<ProviderUser id={}, uid={}, provider_id={}, user_id={}, username={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.provider_id, self.user_id, self.username, self.is_destroyed, self.created_at)

  def create_session(self):
    return dbi.create(Session, {'provider_user': self})

  def repos(self):
    """
    has_many repos through RepoProviderUser
    """
    repo_provider_users = db.session.query(RepoProviderUser) \
      .options(joinedload(RepoProviderUser.repo)) \
      .filter_by(is_destroyed=False, provider_user_id=self.id).all()

    return [rpu.repo for rpu in repo_provider_users]


class Session(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  provider_user_id = db.Column(db.Integer, db.ForeignKey('provider_user.id'), index=True, nullable=False)
  provider_user = db.relationship('ProviderUser', backref='sessions')
  token = db.Column(db.String(64))

  def __init__(self, provider_user=None, provider_user_id=None, token=None):
    if provider_user_id:
      self.provider_user_id = provider_user_id
    else:
      self.provider_user = provider_user

    self.token = token or auth_util.fresh_secret()

  def __repr__(self):
    return '<Session id={}, provider_user_id={}>'.format(self.id, self.provider_user_id)


class RepoProviderUser(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True, nullable=False)
  repo_id = db.Column(db.Integer, db.ForeignKey('repo.id'), index=True, nullable=False)
  repo = db.relationship('Repo', backref='repo_provider_users')
  provider_user_id = db.Column(db.Integer, db.ForeignKey('provider_user.id'), index=True, nullable=False)
  provider_user = db.relationship('ProviderUser', backref='repo_provider_users')
  role = db.Column(db.Integer, nullable=False)
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  roles = repo_user_roles

  def __init__(self, repo=None, repo_id=None, provider_user=None, provider_user_id=None, role=repo_user_roles.MEMBER):
    self.uid = uuid4().hex

    if repo_id:
      self.repo_id = repo_id
    else:
      self.repo = repo

    if provider_user_id:
      self.provider_user_id = provider_user_id
    else:
      self.provider_user = provider_user

    self.role = role

  def __repr__(self):
    return '<RepoProviderUser id={}, uid={}, repo_id={}, provider_user_id={}, role={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.repo_id, self.provider_user_id, self.role, self.is_destroyed, self.created_at)


class Integration(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True, nullable=False)
  repo_id = db.Column(db.Integer, db.ForeignKey('repo.id'), index=True, nullable=False)
  repo = db.relationship('Repo', back_populates='integration')
  access_token = db.Column(db.String(240))
  meta = db.Column(JSON)
  integration_setting = db.relationship('IntegrationSetting', uselist=False, back_populates='integration')
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, repo=None, repo_id=None, access_token=None, meta=None):
    self.uid = uuid4().hex

    if repo_id:
      self.repo_id = repo_id
    else:
      self.repo = repo

    self.access_token = access_token
    self.meta = meta or {}

  def __repr__(self):
    return '<Integration id={}, uid={}, repo_id={}, meta={}, created_at={}, is_destroyed={}>'.format(
      self.id, self.uid, self.repo_id, self.meta, self.created_at, self.is_destroyed)


class IntegrationSetting(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True, nullable=False)
  integration_id = db.Column(db.Integer, db.ForeignKey('integration.id'), index=True, nullable=False)
  integration = db.relationship('Integration', back_populates='integration_setting')
  retrain_on_merge = db.Column(db.Boolean, server_default='f')

  def __init__(self, integration=None, integration_id=None, retrain_on_merge=False):
    self.uid = uuid4().hex

    if integration_id:
      self.integration_id = integration_id
    else:
      self.integration = integration

    self.retrain_on_merge = retrain_on_merge

  def __repr__(self):
    return '<IntegrationSetting id={}, uid={}, integration_id={}, retrain_on_merge={}>'.format(
      self.id, self.uid, self.integration_id, self.retrain_on_merge)


class Deployment(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True, nullable=False)
  repo_id = db.Column(db.Integer, db.ForeignKey('repo.id'), index=True, nullable=False)
  repo = db.relationship('Repo', backref='deployments')
  sha = db.Column(db.String(360))
  status = db.Column(db.String(60))
  train_job = db.relationship('TrainJob', uselist=False, back_populates='deployment')
  failed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  statuses = ds

  def __init__(self, repo=None, repo_id=None, sha=None, status=ds.CREATED, failed=False):
    self.uid = uuid4().hex

    if repo_id:
      self.repo_id = repo_id
    else:
      self.repo = repo

    self.sha = sha
    self.status = status
    self.failed = failed

  def __repr__(self):
    return '<Deployment id={}, uid={}, repo_id={}, sha={}, status={}, failed={}, created_at={}>'.format(
      self.id, self.uid, self.repo_id, self.sha, self.status, self.failed, self.created_at)


class TrainJob(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  deployment_id = db.Column(db.Integer, db.ForeignKey('deployment.id'), index=True, nullable=False)
  deployment = db.relationship('Deployment', back_populates='train_job')
  started_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
  ended_at = db.Column(db.DateTime)

  def __init__(self, deployment=None, deployment_id=None):
    if deployment_id:
      self.deployment_id = deployment_id
    else:
      self.deployment = deployment

  def end(self):
    return dbi.update(self, {'ended_at': datetime.datetime.utcnow()})

  def duration(self):
    return self.ended_at - self.started_at


class Dataset(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True, nullable=False)
  repo_id = db.Column(db.Integer, db.ForeignKey('repo.id'), index=True, nullable=False)
  repo = db.relationship('Repo', backref='datasets')
  name = db.Column(db.String(240), nullable=False)
  slug = db.Column(db.String(240), index=True, nullable=False)
  retrain_step_size = db.Column(db.Integer)
  last_train_record_count = db.Column(db.Integer)
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
  is_destroyed = db.Column(db.Boolean, server_default='f')

  def __init__(self, repo=None, repo_id=None, name=None, retrain_step_size=None, last_train_record_count=0):
    self.uid = uuid4().hex

    if repo_id:
      self.repo_id = repo_id
    else:
      self.repo = repo

    self.name = name
    self.slug = slugify(name, separator='-', to_lower=True)
    self.retrain_step_size = retrain_step_size
    self.last_train_record_count = last_train_record_count

  def table(self):
    # TODO: This is gonna have to be more unique now
    return '{}_{}'.format(self.repo.slug, self.slug).replace('-', '_')

  def __repr__(self):
    return '<Dataset id={}, uid={}, repo_id={}, name={}, slug={}, retrain_step_size={}, ' \
           'last_train_record_count={}, created_at={}, is_destroyed={}>'.format(
      self.id, self.uid, self.repo_id, self.name, self.slug, self.retrain_step_size,
      self.last_train_record_count, self.created_at, self.is_destroyed)