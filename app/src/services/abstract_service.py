class AbstractService(object):

  def perform(self):
    raise BaseException('method must be defined by child class')