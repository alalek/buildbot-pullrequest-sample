import os

c = BuildmasterConfig = {}

c['projectName'] = "TestProject"
c['projectURL'] = "https://github.com/alalek/test"
c['buildbotURL'] = "http://localhost:8010/"

c['slavePortnum'] = 9989

c['status'] = []

import project_builders

c['slaves'] = project_builders.slaves
c['builders'] = project_builders.builders
c['schedulers'] = project_builders.schedulers

from pullrequest.account import Authz

authz_cfg = Authz(
    # change any of these to True to enable; see the manual for more
    # options
    fileName=os.path.join(os.path.abspath(os.path.dirname(__file__)), '../htpasswd'),
    default_action='auth',
    prRestartBuild='auth',
    prStopBuild='auth',
    prRevertBuild=False,
    prShowPerf=False,
)

from pullrequest.webstatus import WebStatus

import pr_github
#import pr_gitlab
c['status'].append(WebStatus(http_port=8010, authz=authz_cfg,
                             pullrequests=[
                                           pr_github.context
                                           # pr_gitlab.context,
                                           ]))

for b in c['builders']:
    if type(b) == type({}):
        b['builddir'] = '/builds/' + b['builddir']
    else:
        b.builddir = '/builds/' + b.builddir
