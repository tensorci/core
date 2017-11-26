import urllib
import sys
import calendar
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


def time_since_epoch():
  return calendar.timegm(time.gmtime())