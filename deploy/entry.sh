#!/bin/bash

set -x

if [ -f /app/deploy/env.sh ]; then
  . /app/deploy/env.sh
fi

if [ -f /app/config/twistd.pid ]; then
  rm /app/config/twistd.pid
fi

if [ -f /app/deploy/prepare_done ]; then
  echo "Preparation step have been done. Remove deploy/prepare_done to run it again"
else
  /app/deploy/prepare_root.sh || exit 1
  su - appuser -c /app/deploy/prepare.sh || exit 1
  touch /app/deploy/prepare_done
  chown appuser:appgroup /app/deploy/prepare_done
fi

cp /app/deploy/supervisor.conf /etc/supervisor/conf.d/app.conf
if [ -z "$DEBUG" ]; then
  exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
else
  su - appuser -c "DEBUG=${DEBUG} DEBUG_HOST=${DEBUG_HOST} DEBUG_PORT=${DEBUG_PORT} /app/deploy/launch.sh"
fi
