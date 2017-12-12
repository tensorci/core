def handle_job_failure(job, exc_type, exc_value, traceback):
  print 'Handling job failure...\n'
  print 'JOB: {}\n'.format(job)
  print 'EXC_TYPE: {}\n'.format(exc_type)
  print 'EXC_VALUE: {}\n'.format(exc_value)
  print 'TRACEBACK: {}'.format(traceback)