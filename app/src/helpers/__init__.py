import urllib
import sys
import time

if sys.version_info[0] < 3:
  unquote = urllib.unquote
  quote = urllib.quote
else:
  unquote = urllib.parse.unquote
  quote = urllib.parse.quote


def decode_url_encoded_str(string):
  return unquote(string)


def url_encode_str(string):
  return quote(string)


def ms_since_epoch(as_int=False):
  ms = time.time() * 1000

  if as_int:
    return int(round(ms))

  return ms