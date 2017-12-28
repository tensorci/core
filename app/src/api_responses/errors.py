# Generic Errors
UNAUTHORIZED = {'ok': False, 'code': 401, 'error': 'unauthorized'}, 401
UNKNOWN_ERROR = {'ok': False, 'code': 500, 'error': 'unknown_error'}, 500
FORBIDDEN = {'ok': False, 'code': 403, 'error': 'forbidden'}, 403
INVALID_INPUT_PAYLOAD = {'ok': False, 'code': 400, 'error': 'invalid_input_payload'}, 400

# Team Errors
TEAM_NAME_TAKEN = {'ok': False, 'code': 1100, 'error': 'team_name_taken'}, 500
TEAM_NOT_FOUND = {'ok': False, 'code': 1101, 'error': 'team_not_found'}, 404

# Prediction Errors
PREDICTION_NAME_TAKEN = {'ok': False, 'code': 1200, 'error': 'prediction_name_taken'}, 500
PREDICTION_NOT_FOUND = {'ok': False, 'code': 1201, 'error': 'prediction_not_found'}, 404
PREDICTION_CREATION_FAILED = {'ok': False, 'code': 1202, 'error': 'prediction_creation_failed'}, 500
NO_COMMITS_IN_REPO = {'ok': False, 'code': 1203, 'error': 'no_commits_found_in_repo'}, 500
ERROR_FETCHING_REPO = {'ok': False, 'code': 1204, 'error': 'error_fetching_repo'}, 500
ERROR_PARSING_COMMITS_FOR_REPO = {'ok': False, 'code': 1205, 'error': 'error_parsing_repo_commits'}, 500
ERROR_PULLING_MODEL_FILE = {'ok': False, 'code': 1206, 'error': 'error_pulling_model_file'}, 500
NO_MODEL_FILE_FOUND = {'ok': False, 'code': 1207, 'error': 'no_model_file_found', 'log': 'No model file found.'}, 404

# User Errors
AUTHENTICATION_FAILED = {'ok': False, 'code': 1300, 'error': 'authentication_failed'}, 401

# Deployment Errors
NO_DEPLOYMENT_TO_SERVE = {'ok': False, 'code': 1400, 'error': 'no_deployment_to_serve'}, 404
LATEST_DEPLOYMENT_TRAINING = {'ok': False, 'code': 1401, 'error': 'latest_deployment_still_training'}, 500

# Dataset Errors
DATASET_NAME_TAKEN = {'ok': False, 'code': 1500, 'error': 'dataset_name_taken'}, 500
DATASET_CREATION_FAILED = {'ok': False, 'code': 1501, 'error': 'dataset_creation_failed'}, 500
NO_FILE_PROVIDED = {'ok': False, 'code': 1502, 'error': 'no_file_provided'}, 500

# Bucket Errors
BUCKET_NOT_FOUND = {'ok': False, 'code': 1600, 'error': 'bucket_not_found'}, 404

# OAuth Errors
INVALID_OAUTH_TEMP_CODE = {'ok': False, 'code': 1701, 'error': 'invalid_oauth_temp_code'}, 500
INVALID_OAUTH_STATE_VALUE = {'ok': False, 'code': 1702, 'error': 'invalid_oauth_state_value'}, 500


# PredictionIntegration Errors
PREDICTION_INTEGRATION_UPSERT_FAILED = {'ok': False, 'code': 1800, 'error': 'prediction_integration_upsert_failed'}, 500

# Provider Errors
PROVIDER_NOT_FOUND = {'ok': False, 'code': 1900, 'error': 'provider_not_found'}, 404
GITHUB_API_USER_ERROR = {'ok': False, 'code': 1901, 'error': 'github_api_user_error'}, 500
GITHUB_API_EMAIL_ERROR = {'ok': False, 'code': 1902, 'error': 'github_api_email_error'}, 500