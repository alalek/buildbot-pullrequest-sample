#!/bin/bash

if [ -f /app/deploy/env.sh ]; then
  . /app/deploy/env.sh
fi

umask 0000
virtualenv --system-site-packages /env
. /env/bin/activate

set -x

pip install pyOpenSSL

(
cd /app/buildbot/master
python setup.py develop
)

[ -d /app/config/pullrequest_ui/package.json ] &&
(
cd /app/config/pullrequest_ui && npm install
)

(
cd /app/config
buildbot --verbose upgrade-master .
)
