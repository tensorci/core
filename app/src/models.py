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
  Team --> has_many --> team_provider_users
  TeamProviderUser --> belongs_to --> Team
  TeamProviderUser --> belongs_to --> ProviderUser
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
  Deployment --> belongs_to --> Commit
  Commit --> has_many --> deployments
  Repo --> has_many --> datasets
  Dataset --> belongs_to --> Repo
  Repo --> has_many --> envs
  Env --> belongs_to --> Repo
"""
import datetime
import importlib
from slugify import slugify
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.types import Text
from src import db, dbi, logger
from sqlalchemy.orm import joinedload
from helpers import auth_util, repo_user_roles, instance_types, user_verification_statuses, providers, deployment_intents
from helpers.deployment_statuses import ds
from uuid import uuid4
from operator import attrgetter
from config import config
from github import Github
from src.utils import clusters


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

  def client(self):
    clients = {
      providers.GITHUB: Github
    }

    return clients.get(self.slug)

  def abbrev(self):
    abbrevs = {
      providers.GITHUB: 'gh'
    }

    return abbrevs.get(self.slug) or 'unk'

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
  icon = db.Column(db.String)
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, name=None, slug=None, provider=None, provider_id=None, icon=None):
    self.uid = uuid4().hex
    self.name = name
    self.slug = slug or slugify(name, separator='-', to_lower=True)

    if provider_id:
      self.provider_id = provider_id
    else:
      self.provider = provider

    self.icon = icon

  def __repr__(self):
    return '<Team id={}, uid={}, name={}, slug={}, provider_id={}, icon={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.name, self.slug, self.provider_id, self.icon, self.is_destroyed, self.created_at)


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


class TeamProviderUser(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  team_id = db.Column(db.Integer, db.ForeignKey('team.id'), index=True, nullable=False)
  team = db.relationship('Team', backref='team_provider_users')
  provider_user_id = db.Column(db.Integer, db.ForeignKey('provider_user.id'), index=True, nullable=False)
  provider_user = db.relationship('ProviderUser', backref='team_provider_users')
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, team=None, team_id=None, provider_user=None, provider_user_id=None):
    if team_id:
      self.team_id = team_id
    else:
      self.team = team

    if provider_user_id:
      self.provider_user_id = provider_user_id
    else:
      self.provider_user = provider_user

  def __repr__(self):
    return '<TeamProviderUser id={}, team_id={}, provider_user_id={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.team_id, self.provider_user_id, self.is_destroyed, self.created_at)


class Repo(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True, nullable=False)
  team_id = db.Column(db.Integer, db.ForeignKey('team.id'), index=True, nullable=False)
  team = db.relationship('Team', backref='repos')
  name = db.Column(db.String(240))
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

  def __init__(self, team=None, team_id=None, name=None, slug=None, elb=None, domain=None, image_repo_owner=None,
               deploy_name=None, client_id=None, client_secret=None, model_ext=None, internal_msg_token=None):
    self.uid = uuid4().hex

    if team_id:
      self.team_id = team_id
    else:
      self.team = team

    self.name = name
    self.slug = slug or slugify(self.name, separator='-', to_lower=True)
    self.elb = elb

    if not domain:
      # TODO: Incorporate provider slug when you start using multiple providers.
      domain = '{}-{}.{}'.format(self.team.slug, self.slug, config.DOMAIN)

    self.domain = domain
    self.image_repo_owner = image_repo_owner or config.IMAGE_REPO_OWNER
    self.deploy_name = deploy_name
    self.client_id = client_id or uuid4().hex
    self.client_secret = client_secret or auth_util.fresh_secret()
    self.model_ext = model_ext
    self.internal_msg_token = internal_msg_token or auth_util.fresh_secret()

  def __repr__(self):
    return '<Repo id={}, uid={}, team_id={}, name={}, slug={}, elb={}, domain={}, ' \
           'image_repo_owner={}, deploy_name={}, model_ext={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.team_id, self.name, self.slug, self.elb, self.domain,
      self.image_repo_owner, self.deploy_name, self.model_ext, self.is_destroyed, self.created_at)

  def ordered_deployments(self):
    return sorted(self.deployments, key=attrgetter('intent_updated_at'), reverse=True)

  def model_file(self):
    if not self.model_ext:
      return None

    return '{}.{}'.format(self.slug, self.model_ext)

  def api_url(self):
    return 'https://{}/api'.format(self.domain)

  def full_name(self):
    return '{}/{}'.format(self.team.name, self.name)

  def url(self):
    team = self.team
    provider = team.provider
    return '{}/{}/{}'.format(provider.url(), team.slug, self.slug)

  def formatted_envs(self, cluster=None):
    query = {'repo': self}

    if cluster:
      query['for_cluster'] = cluster

    envs = dbi.find_all(Env, query)

    def sorted_envs(env_list):
      data = [{
        'uid': env.uid,
        'name': env.name,
        'value': env.value
      } for env in env_list]

      data.sort(key=lambda e: e['name'].lower())
      return data

    # Return here if only one cluster desired.
    if cluster:
      return sorted_envs(envs)

    train_envs = []
    api_envs = []

    for env in envs:
      if env.for_cluster == clusters.TRAIN:
        train_envs.append(env)
      elif env.for_cluster == clusters.API:
        api_envs.append(env)

    return {
      'train_envs': sorted_envs(train_envs),
      'api_envs': sorted_envs(api_envs)
    }


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
  icon = db.Column(db.String)
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, provider=None, provider_id=None, user=None, user_id=None, username=None, access_token=None, icon=None):
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
    self.icon = icon

  def __repr__(self):
    return '<ProviderUser id={}, uid={}, provider_id={}, user_id={}, username={}, icon={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.provider_id, self.user_id, self.username, self.icon, self.is_destroyed, self.created_at)

  def create_session(self):
    return dbi.create(Session, {'provider_user': self})

  def authed_instance(self):
    provider = self.provider
    provider_client = provider.client()

    if provider.slug == providers.GITHUB:
      return provider_client(self.access_token, per_page=100).get_user()

  def repos(self):
    """
    :has_many: repos through RepoProviderUser
    """

    repo_ids = [r.repo_id for r in dbi.find_all(RepoProviderUser, {'provider_user_id': self.id})]

    return db.session.query(Repo) \
      .options(joinedload(Repo.team)) \
      .filter(Repo.id.in_(repo_ids)) \
      .filter_by(is_destroyed=False).all()

    return [rpu.repo for rpu in repo_provider_users]

  def available_repos(self):
    """
    Get all available repos for a provider user through the external provider service
    (e.g. Get all Github repos for a Github user)
    """
    authed_provider_user = self.authed_instance()
    return [r for r in authed_provider_user.get_repos()]


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

  def __init__(self, repo=None, repo_id=None, provider_user=None, provider_user_id=None, role=repo_user_roles.MEMBER_READ):
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

  def has_write_access(self):
    return self.role >= self.roles.MEMBER_WRITE

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
  status = db.Column(db.String(60))
  train_job = db.relationship('TrainJob', uselist=False, back_populates='deployment')
  commit_id = db.Column(db.Integer, db.ForeignKey('commit.id'), index=True, nullable=False)
  commit = db.relationship('Commit', backref='deployments')
  train_triggered_by = db.Column(db.String(120))
  serve_triggered_by = db.Column(db.String(120))
  intent = db.Column(db.String(120))
  intent_updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
  failed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  statuses = ds
  intents = deployment_intents

  def __init__(self, repo=None, repo_id=None, commit=None, commit_id=None, status=ds.CREATED,
               failed=False, train_triggered_by=None, serve_triggered_by=None, intent=None, intent_updated_at=None):
    self.uid = uuid4().hex

    if repo_id:
      self.repo_id = repo_id
    else:
      self.repo = repo

    if commit_id:
      self.commit_id = commit_id
    else:
      self.commit = commit

    self.status = status
    self.failed = failed
    self.train_triggered_by = train_triggered_by
    self.serve_triggered_by = serve_triggered_by
    self.intent = intent
    self.intent_updated_at = intent_updated_at or datetime.datetime.utcnow()

  def __repr__(self):
    return '<Deployment id={}, uid={}, repo_id={}, status={}, commit_id={}, train_triggered_by={}, ' \
           'serve_triggered_by={}, intent={}, intent_updated_at={}, failed={}, created_at={}>'.format(
      self.id, self.uid, self.repo_id, self.status, self.commit_id, self.train_triggered_by,
      self.serve_triggered_by, self.intent, self.intent_updated_at, self.failed, self.created_at)

  def fail(self):
    dbi.update(self, {'failed': True})

    train_job = self.train_job

    # Mark TrainJob as ended
    if train_job and not train_job.ended_at:
      train_job.end()

  def status_greater_than(self, status):
    ss = self.statuses.statuses
    return ss.index(self.status) > ss.index(status)

  def status_less_than(self, status):
    ss = self.statuses.statuses
    return ss.index(self.status) < ss.index(status)

  def intent_to_train(self):
    return self.intent == self.intents.TRAIN

  def intent_to_serve(self):
    return self.intent == self.intents.SERVE

  def readable_status(self):
    return {
      ds.CREATED: 'Created',
      ds.TRAIN_BUILD_SCHEDULED: 'Building Train Image',
      ds.BUILDING_FOR_TRAIN: 'Building Train Image',
      ds.DONE_BUILDING_FOR_TRAIN: 'Deploying For Training',
      ds.TRAINING_SCHEDULED: 'Deploying For Training',
      ds.TRAINING: 'Training',
      ds.DONE_TRAINING: 'Trained',
      ds.API_BUILD_SCHEDULED: 'Building API Image',
      ds.BUILDING_FOR_API: 'Building API Image',
      ds.DONE_BUILDING_FOR_API: 'Deploying To API',
      ds.PREDICTING_SCHEDULED: 'Deploying To API',
      ds.PREDICTING: 'Predicting'
    }.get(self.status)

  def succeeded(self):
    return not self.failed and \
           ((self.intent_to_train() and self.status == self.statuses.DONE_TRAINING) or \
            (self.intent_to_serve() and self.status == self.statuses.PREDICTING))

  def train_deploy_log(self):
    return 'train-deploy:{}'.format(self.uid)

  def api_deploy_log(self):
    return 'api-deploy:{}'.format(self.uid)

  def train_log(self):
    return 'train:{}'.format(self.uid)


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
    return (self.ended_at or datetime.datetime.utcnow()) - self.started_at

  def __repr__(self):
    return '<TrainJob id={}, deployment_id={}, started_at={}, ended_at={}>'.format(
      self.id, self.deployment_id, self.started_at, self.ended_at)


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
    return '{}_{}'.format(self.slug, self.uid).replace('-', '_')

  def __repr__(self):
    return '<Dataset id={}, uid={}, repo_id={}, name={}, slug={}, retrain_step_size={}, ' \
           'last_train_record_count={}, created_at={}, is_destroyed={}>'.format(
      self.id, self.uid, self.repo_id, self.name, self.slug, self.retrain_step_size,
      self.last_train_record_count, self.created_at, self.is_destroyed)


class Commit(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  sha = db.Column(db.String(360), unique=True, nullable=False, index=True)
  message = db.Column(Text)
  author = db.Column(db.String(240))
  author_icon = db.Column(db.String(240))
  branch = db.Column(db.String(120))

  def __init__(self, sha=None, message=None, author=None, author_icon=None, branch='master'):
    self.sha = sha
    self.message = message
    self.author = author
    self.author_icon = author_icon
    self.branch = branch

  def __repr__(self):
    return '<Commit id={}, sha={}, message={}, author={}, author_icon={}, branch={}>'.format(
      self.id, self.sha, self.message, self.author, self.author_icon, self.branch)


class Env(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True, nullable=False)
  repo_id = db.Column(db.Integer, db.ForeignKey('repo.id'), index=True, nullable=False)
  repo = db.relationship('Repo', backref='envs')
  name = db.Column(db.String, nullable=False)
  value = db.Column(db.String, nullable=False)
  for_cluster = db.Column(db.String(60), nullable=False)
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, repo=None, repo_id=None, name=None, value=None, for_cluster=None):
    self.uid = uuid4().hex

    if repo_id:
      self.repo_id = repo_id
    else:
      self.repo = repo

    self.name = name
    self.value = value
    self.for_cluster = for_cluster

  def __repr__(self):
    return '<Env id={}, uid={}, repo_id={}, name={}, value={}, created_at={}>'.format(
      self.id, self.uid, self.repo_id, self.name, self.value, self.created_at)