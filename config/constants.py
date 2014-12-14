slave = {  # buildslave passwords are stored in the other place
    'linux-slave-x64' : { 'max_builds' : 2, 'properties' : { 'CPUs' : 4 } },
    'windows-slave-x64' : { 'max_builds' : 2, 'properties' : { 'CPUs' : 4 } },
    'macosx-slave' : { 'max_builds' : 2, 'properties' : { 'CPUs' : 4 } },
}

# Git mirror repository
URL_GIT_BASE = r'https://github.com/'
URL_SRC = URL_GIT_BASE + r'alalek/test'

repos = {
    URL_SRC: 'code',
}

class CodeBase:
    def __init__(self, branch):
        self.branch = branch

    def getCodebase(self):
        result = dict()
        result['code'] = { 'repository': URL_SRC, 'branch': self.branch}
        return result

codebase = { }
codebase['master'] = CodeBase('master')

import re

def trace(s):
    print s

def params_without_passwords(params):
    safe_params = params.copy()
    for i in safe_params:
        if re.match(r'.*(pwd|pass|password|login|user).*', i):
            safe_params[i] = "*****"
    return safe_params
