"""
Database schema
---------------

Relationships:

  Team --> has_many --> team_users
  User --> has_many --> team_users
  TeamUser --> belongs_to --> Team
  TeamUser --> belongs_to --> User
  Team --> has_many --> predictions
  Prediction --> belongs_to --> Team
  Team --> has_one --> Cluster
  Cluster --> has_one --> Team
"""

import datetime
from slugify import slugify
from sqlalchemy.dialects.postgresql import JSON
from src import db
from src.helpers import auth_util
from uuid import uuid4


class Team(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid = db.Column(db.String, index=True, unique=True)
  name = db.Column(db.String(240), nullable=False)
  slug = db.Column(db.String(240), index=True, unique=True)
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