from uwsgidecorators import spool


@spool
def queued_task(args):
  print('Args: {}'.format(args))