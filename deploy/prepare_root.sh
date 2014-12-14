#!/bin/bash

set -x

groupadd -r appgroup -g 10000
useradd -u 10000 -r -g appgroup -d /home/appuser -m -s /bin/bash -c "App user" appuser

mkdir -p /env
chown -R appuser:appgroup /env

mkdir -p /builds
chown -R appuser:appgroup /builds
