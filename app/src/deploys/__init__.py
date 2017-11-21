from src.scheduler import delayed, delay_class_method


def create_deploy(deployer, args, method_name='deploy'):
  delayed.add_job(delay_class_method, args=[deployer, args, method_name])