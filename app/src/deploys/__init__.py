from src import delayed
from src.helpers.delay_helper import delay_class_method


def create_deploy(deployer, args, method_name='deploy'):
  delayed.add_job(delay_class_method, args=[deployer, args, method_name])