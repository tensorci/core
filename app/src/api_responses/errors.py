# Generic Errors
UNAUTHORIZED = {'ok': False, 'code': 401, 'error': 'unauthorized'}, 401
UNKNOWN_ERROR = {'ok': False, 'code': 500, 'error': 'unknown_error'}, 500
FORBIDDEN = {'ok': False, 'code': 403, 'error': 'forbidden'}, 403

# Team Errors
TEAM_NAME_TAKEN = {'ok': False, 'code': 1100, 'error': 'team_name_taken'}, 500
TEAM_NOT_FOUND = {'ok': False, 'code': 1101, 'error': 'team_not_found'}, 404

# Prediction Errors
PREDICTION_NAME_TAKEN = {'ok': False, 'code': 1200, 'error': 'prediction_name_taken'}, 500
PREDICTION_NOT_FOUND = {'ok': False, 'code': 1201, 'error': 'prediction_not_found'}, 404