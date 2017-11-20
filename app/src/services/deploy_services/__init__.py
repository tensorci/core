from src.scheduler import delayed, delay_class_method


def create_deploy(deployer, args):
  delayed.add_job(delay_class_method, args=[deployer, args, 'deploy'])