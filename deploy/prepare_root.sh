#!/bin/bash

set -x

groupadd -r appgroup -g $APP_GID
useradd -u $APP_UID -r -g appgroup -d /home/appuser -m -s /bin/bash -c "App user" appuser

mkdir -p /env
chown -R appuser:appgroup /env

mkdir -p /builds
chown -R appuser:appgroup /builds
