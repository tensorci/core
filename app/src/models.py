"""
Tables:

  Team
  User
  Token
  TeamUser
  Cluster
  Prediction

Relationships:

  Team --> has_many --> team_users
  User --> has_many --> team_users
  User --> has_many --> tokens
  Token --> belongs_to --> User
  TeamUser --> belongs_to --> Team
  TeamUser --> belongs_to --> User
  Team --> has_one --> Cluster
  Cluster --> has_one --> Team
  Cluster --> has_one --> Bucket
  Bucket --> has_one --> Cluster
  Team --> has_many --> predictions
  Prediction --> belongs_to --> Team
  Prediction --> has_many --> deployments
  Deployment --> belongs_to --> Prediction
  Deployment --> has_one --> TrainJob
  TrainJob --> has_one --> Deployment
  Prediction --> has_many --> datasets
  Dataset --> belongs_to --> Prediction
  Prediction --> has_one --> PredictionSetting
  PredictionSetting --> has_one --> Prediction
  PredictionIntegration --> belongs_to --> Prediction
  PredictionIntegration --> belongs_to --> Integration
  Prediction --> has_many --> prediction_integrations
  Integration --> has_many --> prediction_integrations
"""
import datetime
from slugify import slugify
from sqlalchemy.dialects.postgresql import JSON
from src import db, dbi, logger
from helpers import auth_util, team_user_roles, user_verification_statuses, instance_types
from helpers.deployment_statuses import ds
from uuid import uuid4
from operator import attrgetter
from config import get_config

config = get_config()


class Team(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True)
  name = db.Column(db.String(240), nullable=False)
  slug = db.Column(db.String(240), index=True, unique=True)
  cluster = db.relationship('Cluster', uselist=False, back_populates='team')
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, name=None):
    self.uid = uuid4().hex
    self.name = name
    self.slug = slugify(name, separator='-', to_lower=True)

  def __repr__(self):
    return '<Team id={}, uid={}, name={}, slug={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.name, self.slug, self.is_destroyed, self.created_at)


class User(db.Model):
  ver_statuses = user_verification_statuses
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True)
  email = db.Column(db.String(120), index=True, unique=True)
  name = db.Column(db.String(120), nullable=True)
  hashed_pw = db.Column(db.String(120), nullable=True)
  verification_status = db.Column(db.Integer)
  verification_secret = db.Column(db.String(64))
  reset_pw_secret = db.Column(db.String(64))
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, email=None, name=None, hashed_pw=None, verification_status=user_verification_statuses.NOT_CONTACTED):
    self.uid = uuid4().hex
    self.email = email
    self.name = name
    self.hashed_pw = hashed_pw
    self.verification_status = verification_status
    self.verification_secret = auth_util.fresh_secret()

  def __repr__(self):
    return '<User id={}, uid={}, email={}, name={}, verification_status={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.email, self.name, self.verification_status, self.is_destroyed, self.created_at)

  # return teams through team_user
  def teams(self):
    team_ids = [tu.team_id for tu in self.team_users]

    if not team_ids:
      return []

    return dbi.find_all(Team, {'id': team_ids})

  def team_for_slug(self, slug):
    team_ids = [tu.team_id for tu in self.team_users]

    if not team_ids:
      return None

    team = dbi.find_all(Team, {'id': team_ids, 'slug': slug})

    if not team:
      return None

    return team[0]


class Token(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True, nullable=False)
  user = db.relationship('User', backref='tokens')
  secret = db.Column(db.String(64))

  def __init__(self, user=None, secret=None):
    self.user = user
    self.secret = secret or auth_util.fresh_secret()

  def __repr__(self):
    return '<Token id={}, user_id={}>'.format(self.id, self.user_id)


class TeamUser(db.Model):
  roles = team_user_roles
  id = db.Column(db.Integer, primary_key=True)
  team_id = db.Column(db.Integer, db.ForeignKey('team.id'), index=True, nullable=False)
  team = db.relationship('Team', backref='team_users')
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True, nullable=False)
  user = db.relationship('User', backref='team_users')
  role = db.Column(db.Integer)
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, team=None, user=None, team_id=None, user_id=None, role=team_user_roles.MEMBER):
    if team_id:
      self.team_id = team_id
    else:
      self.team = team

    if user_id:
      self.user_id = user_id
    else:
      self.user = user

    self.role = role

  def __repr__(self):
    return '<TeamUser id={}, team_id={}, user_id={}, role={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.team_id, self.user_id, self.role, self.is_destroyed, self.created_at)


class Cluster(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True)
  team_id = db.Column(db.Integer, db.ForeignKey('team.id'), index=True)
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

  def __init__(self, team=None, ns_addresses=None, hosted_zone_id=None, zones=None,
               master_type=instance_types.MICRO, node_type=instance_types.MICRO, image='ubuntu-16.04'):
    self.uid = uuid4().hex
    self.team = team
    self.name = '{}-cluster.{}'.format(team.slug, config.DOMAIN)
    self.ns_addresses = ns_addresses or []
    self.hosted_zone_id = hosted_zone_id
    self.zones = zones or ['us-west-1a']  # TODO: Ensure zones are all us-west-1
    self.master_type = master_type
    self.node_type = node_type
    self.image = image

  def __repr__(self):
    return '<Cluster id={}, uid={}, team_id={}, name={}, ns_addresses={}, hosted_zone_id={}, zones={}, master_type={}, ' \
           'node_type={}, image={}, validated={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.team_id, self.name, self.ns_addresses, self.hosted_zone_id, self.zones, self.master_type,
      self.node_type, self.image, self.validated, self.is_destroyed, self.created_at)


class Prediction(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True)
  team_id = db.Column(db.Integer, db.ForeignKey('team.id'), index=True, nullable=False)
  team = db.relationship('Team', backref='predictions')
  name = db.Column(db.String(240), nullable=False)
  slug = db.Column(db.String(240), index=True, unique=True)
  elb = db.Column(db.String(240))
  domain = db.Column(db.String(360))
  git_repo = db.Column(db.String(240), index=True)
  image_repo_owner = db.Column(db.String(120))
  deploy_name = db.Column(db.String(360))
  client_id = db.Column(db.String(240))
  client_secret = db.Column(db.String(240))
  model_ext = db.Column(db.String(60))
  internal_msg_token = db.Column(db.String(240))
  prediction_setting = db.relationship('PredictionSetting', uselist=False, back_populates='prediction')
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, team=None, team_id=None, name=None, elb=None, domain=None, git_repo=None,
               image_repo_owner=None, deploy_name=None, client_id=None, client_secret=None,
               model_ext=None, internal_msg_token=None):

    self.uid = uuid4().hex

    if team_id:
      self.team_id = team_id
    else:
      self.team = team

    self.name = name
    self.slug = slugify(name, separator='-', to_lower=True)
    self.elb = elb
    self.domain = domain or '{}.{}'.format(self.slug, config.DOMAIN)
    self.git_repo = git_repo
    self.image_repo_owner = image_repo_owner or config.IMAGE_REPO_OWNER
    self.deploy_name = deploy_name
    self.client_id = client_id or uuid4().hex
    self.client_secret = client_secret or auth_util.fresh_secret()
    self.model_ext = model_ext
    self.internal_msg_token = internal_msg_token or auth_util.fresh_secret()

  def __repr__(self):
    return '<Prediction id={}, uid={}, team_id={}, name={}, slug={}, elb={}, domain={}, ' \
           'git_repo={}, image_repo_owner={}, deploy_name={}, model_ext={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.team_id, self.name, self.slug, self.elb, self.domain,
      self.git_repo, self.image_repo_owner, self.deploy_name, self.model_ext, self.is_destroyed, self.created_at)

  def ordered_deployments(self):
    return sorted(self.deployments, key=attrgetter('created_at'), reverse=True)

  def model_file(self):
    if not self.model_ext:
      return None

    return '{}.{}'.format(self.slug, self.model_ext)

  def api_url(self):
    return 'https://{}/api'.format(self.domain)


class Bucket(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  cluster_id = db.Column(db.Integer, db.ForeignKey('cluster.id'), index=True)
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


class Deployment(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True)
  prediction_id = db.Column(db.Integer, db.ForeignKey('prediction.id'), index=True, nullable=False)
  prediction = db.relationship('Prediction', backref='deployments')
  sha = db.Column(db.String(360))
  status = db.Column(db.String(60))
  train_job = db.relationship('TrainJob', uselist=False, back_populates='deployment')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
  failed = db.Column(db.Boolean, server_default='f')
  statuses = ds

  def __init__(self, prediction=None, prediction_id=None, sha=None, status=ds.CREATED):
    self.uid = uuid4().hex

    if prediction_id:
      self.prediction_id = prediction_id
    else:
      self.prediction = prediction

    self.sha = sha
    self.status = status

  def __repr__(self):
    return '<Deployment id={}, uid={}, prediction_id={}, sha={}, status={}, created_at={}, failed={}>'.format(
      self.id, self.uid, self.prediction_id, self.sha, self.status, self.created_at, self.failed)


class Dataset(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True)
  prediction_id = db.Column(db.Integer, db.ForeignKey('prediction.id'), index=True, nullable=False)
  prediction = db.relationship('Prediction', backref='datasets')
  name = db.Column(db.String(240), nullable=False)
  slug = db.Column(db.String(240), index=True, nullable=False)
  retrain_step_size = db.Column(db.Integer)
  last_train_record_count = db.Column(db.Integer)
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
  is_destroyed = db.Column(db.Boolean, server_default='f')

  def __init__(self, prediction=None, prediction_id=None, name=None,
               retrain_step_size=None, last_train_record_count=0):
    self.uid = uuid4().hex

    if prediction_id:
      self.prediction_id = prediction_id
    else:
      self.prediction = prediction

    self.name = name
    self.slug = slugify(name, separator='-', to_lower=True)
    self.retrain_step_size = retrain_step_size
    self.last_train_record_count = last_train_record_count

  def table(self):
    return '{}_{}'.format(self.prediction.slug, self.slug).replace('-', '_')

  def __repr__(self):
    return '<Dataset id={}, uid={}, prediction_id={}, name={}, slug={}, created_at={}, is_destroyed={}>'.format(
      self.id, self.uid, self.prediction_id, self.name, self.slug, self.retrain_step_size,
      self.last_train_record_count, self.created_at, self.is_destroyed)


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


class PredictionSetting(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  prediction_id = db.Column(db.Integer, db.ForeignKey('prediction.id'), index=True, nullable=False)
  prediction = db.relationship('Prediction', back_populates='prediction_setting')
  retrain_on_merge = db.Column(db.Boolean, server_default='f')

  def __init__(self, prediction=None, prediction_id=None, retrain_on_merge=False):
    if prediction_id:
      self.prediction_id = prediction_id
    else:
      self.prediction = prediction

    self.retrain_on_merge = retrain_on_merge

  def __repr__(self):
    return '<PredictionSetting id={}, prediction_id={}, retrain_on_merge={}>'.format(
      self.id, self.prediction_id, self.retrain_on_merge)


class Integration(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True)
  name = db.Column(db.String(240), nullable=False)
  slug = db.Column(db.String(240), index=True, unique=True)
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
  is_destroyed = db.Column(db.Boolean, server_default='f')

  def __init__(self, name=None):
    self.uid = uuid4().hex
    self.name = name
    self.slug = slugify(name, separator='_', to_lower=True)

  def __repr__(self):
    return '<Integration id={}, uid={}, name={}, slug={}, created_at={}, is_destroyed={}>'.format(
      self.id, self.uid, self.name, self.slug, self.created_at, self.is_destroyed)


class PredictionIntegration(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True)
  prediction_id = db.Column(db.Integer, db.ForeignKey('prediction.id'), index=True, nullable=False)
  prediction = db.relationship('Prediction', backref='prediction_integrations')
  integration_id = db.Column(db.Integer, db.ForeignKey('integration.id'), index=True, nullable=False)
  integration = db.relationship('Integration', backref='prediction_integrations')
  api_key = db.Column(db.String(360))
  meta = db.Column(JSON)
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, prediction=None, prediction_id=None, integration=None,
               integration_id=None, api_key=None, meta=None):
    self.uid = uuid4().hex

    if prediction_id:
      self.prediction_id = prediction_id
    else:
      self.prediction = prediction

    if integration_id:
      self.integration_id = integration_id
    else:
      self.integration = integration

    self.api_key = api_key
    self.meta = meta or {}

  def __repr__(self):
    return '<PredictionIntegration id={}, uid={}, prediction_id={}, integration_id={}, api_key={}, meta={}, created_at={}, is_destroyed={}>'.format(
      self.id, self.uid, self.prediction_id, self.integration_id, self.api_key, self.meta, self.created_at, self.is_destroyed)