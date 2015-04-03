Buildbot pullrequest plugin sample
==================================


This repository uses Git submodules, so clone it via this command:

```
  git clone --recursive <URL>
```


Requirements
------------

* Install docker: https://docs.docker.com/installation/


Installation
------------

* Run deploy script:

  ./deploy.sh

This script creates deploy/env.sh file to store settings and builds docker image (image name is buildbot_image).
Edit deploy/env.sh and setup proper settings.

* Create container and run:

```
  docker run -it \
    -p 8010:8010 -p 9989:9989 \
    --name buildbot \
    -v `pwd`:/app \
    buildbot_image
```

* Start container again:

  docker start buildbot

* Start with attached console (for debug purpose, Ctrl+C will stop container):

  docker start -ai buildbot

* Stop container:

  docker stop buildbot

* Destroy container:

  docker rm buildbot


Debug support
-------------

These steps enable debug for PyDev package from Eclipse.

Container creation:

```
  docker run -it \
    -p 8010:8010 -p 9989:9989 \
    --name buildbot-debug \
    --env DEBUG=1 \
    -v `pwd`:/app \
    buildbot_image
```

Folder `pysrc` is distributed with PyDev package. Find it on your development machine and copy to project directory.

Modify pydevd_file_utils.py:

```
PATHS_FROM_ECLIPSE_TO_PYTHON = [
    (r'<path to current dir>', r'/app'),
]
```
