"""
Utilities for account security.
"""

# The purpose of applying sha512 before bcrypt is to allow arbitrarily long
# passwords without loss of entropy or DDoS vulnerability. See
# https://blogs.dropbox.com/tech/2016/09/how-dropbox-securely-stores-your-passwords/
# for more info.
#
# TODO: Investigate using a pepper and hashing on separate machines than the
# ones running the API. This would protect the pepper in case the API is
# compromised, and allow hashing on machines suitable for a compute heavy
# workload.

import base64
import hmac
import os

from passlib.hash import bcrypt
from passlib.hash import hex_sha512


def hash_pw(password):
  # type: (str) -> bytes
  """
  :param password: The password to hash.
  :returns: The hashed password.
  """
  return bcrypt.using(rounds=10).hash(hex_sha512.hash(password))


def verify_pw(hashed_password, password):
  # type (bytes, str) -> bool
  """
  :param: hashed_password. The hashed password.
  :param: password The password.

  >>> verify_pw(hash_pw('hunter2'), 'hunter2')
  True
  >>> verify_pw(hash_pw('hunter2'), 'hunter1')
  False
  >>> verify_pw(b'garbage', 'hunter1')
  False
  """
  try:
    return bcrypt.verify(hex_sha512.hash(password), hashed_password)
  except ValueError:
    return False


def fresh_secret():
  # type () -> str
  """
  :returns: 32 bytes of cryptographically secure randomness, base64 encoded.
            Safe for inclusion in urls. In particular, guaranteed not to
            include an '%' characters.
  """
  return base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')


def verify_secret(secret1, secret2):
  """
  :returns: True if secret1 == secret2. Uses a constant time string compare.
  """
  return hmac.compare_digest(secret1, secret2)


def serialize_token(token_id, secret):
  """
  :returns: <token_id>%<secret>
  """
  return str(token_id) + '%' + secret


def unserialize_token(token):
  """
  :returns: {token_id, secret}

  >>> token_id = 1
  >>> secret = fresh_secret()
  >>> token = serialize_token(token_id, secret)
  >>> x = unserialize_token(token)
  >>> x['token_id']
  1
  >>> 'secret' in x
  True
  >>> len(x.items())
  2
  """
  # TODO do something graceful when unserializing fails.
  token_id, secret = token.split('%')
  return dict(token_id=int(token_id), secret=secret)