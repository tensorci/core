# Generic Errors
UNAUTHORIZED = {'ok': False, 'code': 401, 'error': 'unauthorized'}, 401
UNKNOWN_ERROR = {'ok': False, 'code': 500, 'error': 'unknown_error'}, 500
FORBIDDEN = {'ok': False, 'code': 403, 'error': 'forbidden'}, 403
INVALID_INPUT_PAYLOAD = {'ok': False, 'code': 400, 'error': 'invalid_input_payload'}, 400

# Team Errors
TEAM_NAME_TAKEN = {'ok': False, 'code': 1100, 'error': 'team_name_taken'}, 500
TEAM_NOT_FOUND = {'ok': False, 'code': 1101, 'error': 'team_not_found'}, 404
ORG_TO_TEAM_CONVERSION_FAILED = {'ok': False, 'code': 1102, 'error': 'team_creation_from_org_failed'}, 500

# Repo Errors
NO_COMMITS_IN_REPO = {'ok': False, 'code': 1200, 'error': 'no_commits_found_in_repo'}, 500
ERROR_FETCHING_REPO = {'ok': False, 'code': 1201, 'error': 'error_fetching_repo'}, 500
ERROR_PARSING_COMMITS_FOR_REPO = {'ok': False, 'code': 1202, 'error': 'error_parsing_repo_commits'}, 500
ERROR_PULLING_MODEL_FILE = {'ok': False, 'code': 1203, 'error': 'error_pulling_model_file'}, 500
NO_MODEL_FILE_FOUND = {'ok': False, 'code': 1204, 'error': 'no_model_file_found', 'log': 'No model file found.'}, 404
INVALID_REPO_PERMISSIONS = {'ok': False, 'code': 1205, 'error': 'action_requires_higher_permissions'}, 401
REPO_NOT_REGISTERED = {'ok': False, 'code': 1206, 'error': 'repo_not_registered'}, 404
REPO_NOT_FOUND = {'ok': False, 'code': 1207, 'error': 'repo_not_found'}, 404
ERROR_FETCHING_AVAILABLE_REPOS = {'ok': False, 'code': 1208, 'error': 'error_fetching_available_external_repos'}, 500

# ProviderUser Errors
AUTHENTICATION_FAILED = {'ok': False, 'code': 1300, 'error': 'authentication_failed'}, 401

# Deployment Errors
NO_DEPLOYMENT_TO_SERVE = {'ok': False, 'code': 1400, 'error': 'no_deployment_to_serve'}, 404

# Dataset Errors
DATASET_NAME_TAKEN = {'ok': False, 'code': 1500, 'error': 'dataset_name_taken'}, 500
DATASET_CREATION_FAILED = {'ok': False, 'code': 1501, 'error': 'dataset_creation_failed'}, 500
NO_FILE_PROVIDED = {'ok': False, 'code': 1502, 'error': 'no_file_provided'}, 500
DATASET_NOT_FOUND = {'ok': False, 'code': 1503, 'error': 'dataset_not_found'}, 404

# Bucket Errors
BUCKET_NOT_FOUND = {'ok': False, 'code': 1600, 'error': 'bucket_not_found'}, 404

# OAuth Errors
INVALID_OAUTH_TEMP_CODE = {'ok': False, 'code': 1701, 'error': 'invalid_oauth_temp_code'}, 500
INVALID_OAUTH_STATE_VALUE = {'ok': False, 'code': 1702, 'error': 'invalid_oauth_state_value'}, 500
INVALID_BETA_ACCESS_CODE = {'ok': False, 'code': 1703, 'error': 'invalid_beta_access_code'}, 500

# Provider Errors
PROVIDER_NOT_FOUND = {'ok': False, 'code': 1800, 'error': 'provider_not_found'}, 404
GITHUB_API_USER_ERROR = {'ok': False, 'code': 1801, 'error': 'github_api_user_error'}, 500
GITHUB_API_EMAIL_ERROR = {'ok': False, 'code': 1802, 'error': 'github_api_email_error'}, 500
PROVIDER_MISMATCH = {'ok': False, 'code': 1803, 'error': 'provider_mismatch'}, 500

# RepoProviderUser Errors
NOT_ASSOCIATED_WITH_REPO = {'ok': False, 'code': 1900, 'error': 'not_yet_associated_with_repo'}, 403
REPO_PROVIDER_USER_NOT_FOUND = {'ok': False, 'code': 1901, 'error': 'repo_provider_user_not_found'}, 404

# User Errors
USER_NOT_FOUND = {'ok': False, 'code': 2000, 'error': 'user_not_found'}, 404

# Deployment Errors
DEPLOYMENT_NOT_FOUND = {'ok': False, 'code': 2100, 'error': 'deployment_not_found'}, 404

# Env Errors
ERROR_UPSERTING_ENVS = {'ok': False, 'code': 2200, 'error': 'error_upserting_envs'}, 500
ENV_NOT_FOUND = {'ok': False, 'code': 2201, 'error': 'env_not_found'}, 404
ERROR_DELETING_ENV = {'ok': False, 'code': 2202, 'error': 'error_deleting_env'}, 500