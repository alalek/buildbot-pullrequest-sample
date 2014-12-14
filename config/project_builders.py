import os
from factory_common import OSType

print "Configure builds..."

import constants
from constants import trace

import buildbot_passwords
from buildbot.buildslave import BuildSlave

slaves = []
for slave in constants.slave:
    trace("Register slave: " + slave + " with passwd=*** and params=(%s)" % constants.slave[slave])
    slaves.append(BuildSlave(slave, buildbot_passwords.slave[slave], **(constants.slave[slave])))


platforms = ['default']

def osTypeParameter(platform, **params):
    if platform == 'default':
        return OSType.all
    assert False

def androidABIParameter(platform, osType, **params):
    return [None]

def androidDeviceParameter(platform, osType, **params):
    return [None]

def androidParameters():
    return [dict(androidABI=androidABIParameter), dict(androidDevice=androidDeviceParameter)]

def is64ParameterCheck(platform, osType, **params):
    if osType == OSType.ANDROID:
        return [None]
    if osType == OSType.WINDOWS:
        return [True, False]
    if osType == OSType.MACOSX:
        return [None]
    return [True]

def is64ParameterPerf(platform, osType, **params):
    return [None]

def is64ParameterPrecommit(platform, osType, **params):
    return [None]

def availableCompilers(platform, osType, **params):
    if osType == OSType.ANDROID:
        return [None]
    if osType == OSType.WINDOWS:
        return ['vc11']
    else:
        return [None]

def precommitCompilers(params):
    return [availableCompilers(params)[0]]

def perfCompilers(platform, osType, **params):
    if osType == OSType.ANDROID:
        return [None]
    if osType == OSType.WINDOWS:
        return ['vc11']
    else:
        return [None]


from factory_builders_aggregator import *
import factory_common

# Current "top-level" factory
BuildFactory = factory_common.CommonFactory

builders = []
schedulers = []

def addConfiguration(descriptor):
    global builders, schedulers
    (new_builders, new_schedulers) = descriptor.Register()
    builders = builders + new_builders
    schedulers = schedulers + new_schedulers

# Nightly builders
for branch in ['master']:
    addConfiguration(
        SetOfBuildersWithSchedulers(branch=branch, nameprefix='check-',
            genForce=True, genNightly=True, nightlyHour=18,
            builders=[
                SetOfBuilders(
                    factory_class=BuildFactory,
                    init_params=dict(branch=branch, useCategory='check' + branch),
                    variate=[
                        dict(platform=platforms),
                        dict(osType=osTypeParameter),
                    ] + androidParameters() + [
                        dict(is64=is64ParameterCheck),
                        dict(compiler=availableCompilers),
                    ]
                ),
            ]
        )
    )

# Precommit builders

class LinuxPrecommit(BuildFactory):
    def __init__(self):
        BuildFactory.__init__(
            self, branch='branch', useCategory='precommit', isPrecommit=True, platform='default',
            builderName='precommit_linux64',
            osType=OSType.LINUX, is64=True)

class WindowsPrecommit(BuildFactory):
    def __init__(self, is64):
        BuildFactory.__init__(
            self, branch='branch', useCategory='precommit', isPrecommit=True, platform='default',
            builderName='precommit_windows%s' % ('64' if is64 else '32'),
            osType=OSType.WINDOWS, is64=is64, compiler='vc11')

class MacOSXPrecommit(BuildFactory):
    def __init__(self):
        BuildFactory.__init__(
            self, branch='branch', useCategory='precommit', isPrecommit=True, platform='default',
            builderName='precommit_macosx',
            osType=OSType.MACOSX, is64=True)

class AndroidPrecommit(BuildFactory):
    def __init__(self):
        BuildFactory.__init__(
            self, branch='branch', useCategory='precommit', isPrecommit=True, platform='default',
            builderName='precommit_android',
            osType=OSType.ANDROID)


addConfiguration(
    SetOfBuildersWithSchedulers(branch=branch, nameprefix='precommit-',
        genForce=True, genNightly=False,
        builders=[
            LinuxPrecommit(),
            WindowsPrecommit(True),
            WindowsPrecommit(False),
            MacOSXPrecommit(),
            AndroidPrecommit(),
        ]
    )
)

print "Configure builds... DONE"
