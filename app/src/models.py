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
"""
import datetime
from slugify import slugify
from sqlalchemy.dialects.postgresql import JSON
from src import db
from helpers import auth_util, team_user_roles, user_verification_statuses, instance_types
from uuid import uuid4
from config import get_config
from statuses.pred_statuses import pstatus

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
  team_id = db.Column(db.Integer, db.ForeignKey('team.id'), index=True)
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
  slug = db.Column(db.String(240), index=True)
  elb = db.Column(db.String(240))
  domain = db.Column(db.String(360))
  git_repo = db.Column(db.String(240))
  image_repo_owner = db.Column(db.String(120))
  image_version = db.Column(db.String(60))
  status = db.Column(db.String(60))
  sha = db.Column(db.String(360))
  deploy_name = db.Column(db.String(360))
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, team=None, team_id=None, name=None, elb=None, domain=None,
               git_repo=None, image_repo_owner=None, image_version='0.0.1',
               status=pstatus.statuses[0], sha=None, deploy_name=None):

    self.uid = uuid4().hex

    if team_id:
      self.team_id = team_id
    else:
      self.team = team

    self.name = name
    self.slug = slugify(name, separator='-', to_lower=True)
    self.elb = elb
    self.domain = domain or '.'.join([self.slug, self.team.slug, config.DOMAIN])
    self.git_repo = git_repo
    self.image_repo_owner = image_repo_owner or config.IMAGE_REPO_OWNER
    self.image_version = image_version
    self.status = status
    self.sha = sha
    self.deploy_name = deploy_name

  def __repr__(self):
    return '<Prediction id={}, uid={}, team_id={}, name={}, slug={}, elb={}, domain={}, ' \
           'git_repo={}, image_repo_owner={}, image_version={}, status={}, sha={}, deploy_name={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.team_id, self.name, self.slug, self.elb, self.domain,
      self.git_repo, self.image_repo_owner, self.image_version, self.status, self.sha, self.deploy_name, self.is_destroyed, self.created_at)

  def dataset_table(self):
    return '{}-{}'.format(self.slug, self.uid)


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