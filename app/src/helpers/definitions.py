import os

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
source_dir = base_dir + '/src'
configs_dir = source_dir + '/configs'

auth_header_name = 'TensorCI-Api-Token'
core_header_name = 'Core-Api-Token'
cookie_name = 'tensorci-user'
tci_keep_alive = '<tci-keep-alive>'