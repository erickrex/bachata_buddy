#!/bin/sh
set -e

# Set default PORT if not provided
export PORT=${PORT:-8080}

# Replace PORT variable in nginx config
envsubst "\$PORT" < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

# Start nginx
exec nginx -g "daemon off;"
