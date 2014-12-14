#!/bin/bash

umask 0000
virtualenv --system-site-packages /env
. /env/bin/activate

set -x

pip install pyOpenSSL

(
cd /app/buildbot/master
python setup.py develop
)

(
cd /app/config/pullrequest_ui && npm install
)

(
cd /app/config
buildbot --verbose upgrade-master .
)
