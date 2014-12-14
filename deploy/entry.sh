#!/bin/bash

set -x

/app/deploy/prepare_root.sh
su - appuser -c /app/deploy/prepare.sh

cp /app/deploy/supervisor.conf /etc/supervisor/conf.d/app.conf
if [ -z "$DEBUG" ]; then
  exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
else
  su - appuser -c "DEBUG=${DEBUG} DEBUG_HOST=${DEBUG_HOST} DEBUG_PORT=${DEBUG_PORT} /app/deploy/launch.sh"
fi
