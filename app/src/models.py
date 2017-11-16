"""
Tables:

  Team
  User
  TeamUser
  Cluster
  Prediction

Relationships:

  Team --> has_many --> team_users
  User --> has_many --> team_users
  TeamUser --> belongs_to --> Team
  TeamUser --> belongs_to --> User
  Team --> has_one --> Cluster
  Cluster --> has_one --> Team
  Team --> has_many --> predictions
  Prediction --> belongs_to --> Team
"""
import datetime
from slugify import slugify
from sqlalchemy.dialects.postgresql import JSON
from src import db
from src.helpers import auth_util
from uuid import uuid4
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
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True)
  email = db.Column(db.String(120), index=True, unique=True)
  name = db.Column(db.String(120), nullable=True)
  hashed_pw = db.Column(db.String(120), nullable=True)
  verification_secret = db.Column(db.String(64))
  verification_status = db.Column(db.Integer)
  reset_pw_secret = db.Column(db.String(64))
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, email=None, name=None, hashed_pw=None, verification_status=0):
    self.uid = uuid4().hex
    self.email = email
    self.name = name
    self.hashed_pw = hashed_pw
    self.verification_secret = auth_util.fresh_secret()
    self.verification_status = verification_status

  def __repr__(self):
    return '<User id={}, uid={}, email={}, name={}, verification_status={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.email, self.name, self.verification_status, self.is_destroyed, self.created_at)


class TeamUser(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  team_id = db.Column(db.Integer, db.ForeignKey('team.id'), index=True, nullable=False)
  team = db.relationship('Team', backref='team_users')
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True, nullable=False)
  user = db.relationship('User', backref='team_users')
  role = db.Column(db.Integer)
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, team=None, user=None, team_id=None, user_id=None, role=0):
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
  team_id = db.Column(db.Integer, db.ForeignKey('team.id'), index=True, nullable=False)
  team = db.relationship('Team', back_populates='cluster')
  name = db.Column(db.String(360), nullable=False)
  ns_addresses = db.Column(JSON)
  zones = db.Column(JSON)
  master_type = db.Column(db.String(120))
  node_type = db.Column(db.String(120))
  image = db.Column(db.String(120))
  validated = db.Column(db.Boolean, server_default='f')
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, team=None, ns_addresses=None, zones=None,
               master_type='t2.micro', node_type='t2.micro', image='ubuntu-16.04'):
    self.uid = uuid4().hex
    self.team = team
    self.name = '{}-cluster.{}'.format(team.slug, config.DOMAIN)
    self.ns_addresses = ns_addresses or []
    self.zones = zones or ['us-west-2a']  # TODO: Ensure zones are all us-west-2
    self.master_type = master_type
    self.node_type = node_type
    self.image = image

  def bucket(self):
    return 's3://{}'.format(self.team.slug)

  def __repr__(self):
    return '<Cluster id={}, uid={}, team_id={}, name={}, ns_addresses={}, zones={}, master_type={}, ' \
           'node_type={}, image={}, valiated={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.team_id, self.name, self.ns_addresses, self.zones, self.master_type,
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
  is_destroyed = db.Column(db.Boolean, server_default='f')
  created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

  def __init__(self, team=None, team_id=None, name=None, elb=None, domain=None,
               git_repo=None, image_repo_owner=None, image_version='0.0.1'):
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

  def __repr__(self):
    return '<Prediction id={}, uid={}, team_id={}, name={}, slug={}, elb={}, domain={}, ' \
           'git_repo={}, image_repo_owner={}, image_version={}, is_destroyed={}, created_at={}>'.format(
      self.id, self.uid, self.team_id, self.name, self.slug, self.elb, self.domain,
      self.git_repo, self.image_repo_owner, self.image_version, self.is_destroyed, self.created_at)