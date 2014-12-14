#!/bin/bash

umask 0000
. /env/bin/activate
cd /app/config
if [ -z "$DEBUG" ]; then
  buildbot --verbose start --nodaemon
else
  python /app/deploy/run_debug.py --verbose restart --nodaemon
fi
