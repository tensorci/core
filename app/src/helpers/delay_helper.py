from src import app


def delay_class_method(klass=None, init_args={}, method_name='perform', method_args={}):
  with app.app_context():
    class_instance = klass(**init_args)
    method = getattr(class_instance, method_name)
    method(**method_args)