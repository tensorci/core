#! /usr/bin/env bash
set -e
# Get the maximum upload file size for Nginx, default to 0: unlimited
USE_NGINX_MAX_UPLOAD=${NGINX_MAX_UPLOAD:-0}
# Generate Nginx config for maximum upload file size
echo "client_max_body_size $USE_NGINX_MAX_UPLOAD;" > /etc/nginx/conf.d/upload.conf

# Get the URL for static files from the environment variable
USE_STATIC_URL=${STATIC_URL:-'/static'}
# Get the absolute path of the static files from the environment variable
USE_STATIC_PATH=${STATIC_PATH:-'/app/static'}
# Get the listen port for Nginx, default to 80
USE_LISTEN_PORT=${LISTEN_PORT:-80}

echo "
[uwsgi]
socket = /tmp/uwsgi.sock
chown-socket = nginx:nginx
chmod-socket = 664
workers = 1
" > /etc/uwsgi/uwsgi.ini

echo "map \$http_upgrade \$connection_upgrade {
    'websocket' upgrade;
    default close;
}" > /etc/nginx/conf.d/aaaaaa.conf

# Generate Nginx config first part using the environment variables
echo "
server {
    listen ${USE_LISTEN_PORT};
    server_name _;

    location / {
        try_files \$uri @app;
    }

    location @app {
        include uwsgi_params;
        uwsgi_pass unix:///tmp/uwsgi.sock;
    }

    location /socket.io/ {
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_redirect off;

        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';

        proxy_pass http://unix:///tmp/websocket.sock;
    }

    location $USE_STATIC_URL {
        alias $USE_STATIC_PATH;
    }
" > /etc/nginx/conf.d/nginx.conf

# If STATIC_INDEX is 1, serve / with /static/index.html directly (or the static URL configured)
if [[ $STATIC_INDEX == 1 ]] ; then
echo "    location = / {
        index $USE_STATIC_URL/index.html;
    }" >> /etc/nginx/conf.d/nginx.conf
fi
# Finish the Nginx config file
echo "}" >> /etc/nginx/conf.d/nginx.conf

exec "$@"
