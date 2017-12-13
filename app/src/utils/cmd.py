import re
import sys
from subprocess import Popen, PIPE
from src import logger


class CmdComponentException(BaseException):
  def __init__(self, message):
    self.message = message


def execute(cmd,
            bufsize=-1,
            stdout=PIPE,
            stderr=PIPE,
            creationflags=0,
            **subprocess_kwargs):
  """Handles executing a command on the shell and consumes/returns the status, stdout, and stderr.

  :param cmd:
      The command argument list to execute.
      It should be a string, or a sequence of program arguments. The
      program to execute is the first item in the args sequence or string.

  :param subprocess_kwargs:
      Keyword arguments to be passed to subprocess.Popen

  :return:
      * tuple(int(status), str(stdout), str(stderr))
  """
  status = 0
  stdout_value = b''
  stderr_value = b''

  try:
    # Ensure command components are free of sub/nested-commands
    validate_cmd_comps(cmd)
  except CmdComponentException as e:
    logger.error(e.message)
    return status, stdout_value, stderr_value

  try:
    # execute the command
    proc = Popen(cmd,
                 bufsize=bufsize,
                 stdout=stdout,
                 stderr=stderr,
                 creationflags=creationflags,
                 **subprocess_kwargs)
  except OSError as e:
    logger.error('Command not found error -- {} -- for command: {}'.format(e, cmd))
    return status, stdout_value, stderr_value

  try:
    # Read stdout, stderr and the return status of the command
    stdout_value, stderr_value = proc.communicate()

    if stdout_value.endswith(b'\n'):
      stdout_value = stdout_value[:-1]

    if stderr_value.endswith(b'\n'):
      stderr_value = stderr_value[:-1]

    status = proc.returncode
  finally:
    # Close pipes
    proc.stdout.close()
    proc.stderr.close()

  # Safely decode binary string if stdout_value is of that type
  if isinstance(stdout_value, bytes):
    stdout_value = safe_decode(stdout_value)

  return status, stdout_value, safe_decode(stderr_value)


def safe_decode(s):
  """Safely decodes a binary string to unicode"""
  if isinstance(s, unicode):
    return s
  elif isinstance(s, bytes):
    return s.decode(sys.getdefaultencoding(), 'surrogateescape')
  elif s is not None:
    raise TypeError('Expected bytes or text, but got %r' % (s,))


def validate_cmd_comps(comps):
  """Validate that no sub/nested-commands exist in the components of an execute command"""
  for c in comps:
    if c is None:
      raise CmdComponentException('None component found in command: {}'.format(comps))

    if re.match('\$\(.*\)', str(c)):
      raise CmdComponentException('Invalid command -- attempted subcommand {} within full command {}'.format(c, comps))


def bool_response_cmd(cmd):
  """Return a boolean for if the command succeeded or not based off the return status
     Return False if command hits unexpected error.
  """
  try:
    status, stdout, stderr = execute(cmd)
  except BaseException as e:
    logger.error('Command () failed with unknown error: {}'.format(' '.join(cmd), e))
    return False

  if status != 0:
    logger.error('Command () returned non-zero status({}) with error {}'.format(' '.join(cmd), status, stderr))
    return False

  return True