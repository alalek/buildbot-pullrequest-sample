FROM dockerfile/ubuntu

RUN \
  apt-get update && \
  apt-get install -y \
    python python-dev python-pip python-virtualenv libpython2.7-dev libffi-dev python-twisted python-twisted-web \
    npm node \
    supervisor sudo && \
  rm -rf /var/lib/apt/lists/*

RUN [ -x /usr/bin/nodejs ] && ln -s /usr/bin/nodejs /usr/bin/node && \
  npm install -g bower grunt-cli

VOLUME ["/app"]
VOLUME ["/etc/supervisor/conf.d"]

CMD ["/app/deploy/entry.sh"]