from buildbot.config import BuilderConfig
from buildbot.process.factory import BuildFactory
from buildbot.status.results import *
from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand, SetProperty, Compile
from buildbot.steps.slave import RemoveDirectory, MakeDirectory
from buildbot.steps.master import MasterShellCommand
from buildbot.steps.transfer import *
from buildbot.process.properties import Interpolate, renderer

from twisted.internet import defer

import re, datetime

from buildbot.process.build import Build
from buildbot.sourcestamp import SourceStamp

class OSType():
    WINDOWS = 'Win'
    LINUX = 'Lin'
    MACOSX = 'Mac'
    ANDROID = 'Android'

    all = [WINDOWS, LINUX, MACOSX, ANDROID]

    suffix = {
        WINDOWS:'win',
        LINUX:'lin',
        MACOSX:'mac',
        ANDROID:'android'
    }

@defer.inlineCallbacks
def interpolateParameter(value, props):
    if hasattr(value, 'getRenderingFor'):
        value = yield defer.maybeDeferred(value.getRenderingFor, props)
    defer.returnValue(value)

def getDropRoot(masterPath=True):
    return '' if not masterPath else '/data/'

def getDirectroryForPerfData():
    directory = getDropRoot() + 'reports/'
    return directory

def getMergeNeededFn(codebase):
    def mergeNeeded(step):
        ss = step.build.getSourceStamp('%s_merge' % codebase)
        return (ss is not None) and (ss.repository != '')
    return mergeNeeded

def getMergeCommand(codebase, workdir, doStepIf=True):
    def doStepIfFn(step):
        if doStepIf == False or (not doStepIf == True and not doStepIf(step)):
            return False
        return getMergeNeededFn(codebase)(step)
    return ShellCommand(name="Merge %s with test branch" % codebase, haltOnFailure=True,
                        command=Interpolate('git pull -v "%%(src:%s_merge:repository)s" "%%(src:%s_merge:branch)s"' % (codebase, codebase)),
                        workdir=workdir, description="merge %s" % codebase, descriptionDone="merge %s" % codebase,
                        doStepIf=doStepIfFn);

def hideStepIfFn(result, s):
    return result != SUCCESS and result != WARNINGS and result != FAILURE and result != EXCEPTION and result != RETRY

hideStepIfDefault = hideStepIfFn

def getResultFileNameRenderer(testPrefix, test, testSuffix, fileSuffix='xml'):
    @renderer
    def resultFileName(props):
        name = props['timestamp']
        rev = props.getProperty('revision')
        if not rev:
            rev = props.getProperty('got_revision')
            if isinstance(rev, dict):
                rev = rev['code']
        if rev:
            name += '-' + rev[:7]
        else:
            name += '-xxxxxxx'
        build = props.getBuild()
        assert isinstance(build, Build)
        merge_ss = build.getSourceStamp('code_merge')
        if merge_ss:
            assert isinstance(merge_ss, SourceStamp)
            patch_rev = merge_ss.asDict().get('revision')
            if patch_rev:
                name += '-%s' % patch_rev[:7]
        name += ' '
        platform = props.getProperty('platform')
        if platform:
            name += platform + '-'
        name += testPrefix + '_' + test + testSuffix
        pullrequest = props.getProperty('pullrequest')
        if pullrequest:
            branch = props.getProperty('branch')
            mangled_branch = branch.replace(r'.', '_')
            name += ' pr%s %s_' % (pullrequest, mangled_branch)
        else:
            name += ' '
        name += props['buildername'] + '_' + ("%05d" % props['buildnumber']);
        if fileSuffix:
            name += '.' + fileSuffix
        return name
    return resultFileName


class CommonFactory(object):

    SRC_DIR = 'src'

    def __init__(self, **kwargs):
        self.forceSched = kwargs.pop('forceSched', {})

        if not hasattr(self, 'builderName'):
            self.builderName = kwargs.pop('builderName', None)
        if not hasattr(self, 'useName'):
            self.useName = kwargs.pop('useName', None)
        if not hasattr(self, 'useNamePrefix'):
            self.useNamePrefix = kwargs.pop('useNamePrefix', None)
        if not hasattr(self, 'useSlave'):
            self.useSlave = kwargs.pop('useSlave', None)
        if not hasattr(self, 'platform'):
            self.platform = kwargs.pop('platform', None)
        self.branch = kwargs.pop('branch', None)
        self.branchSafeName = self.branch.replace('.', '_') if self.branch else None
        self.osType = kwargs.pop('osType', None)
        self.androidABI = kwargs.pop('androidABI', None)
        assert self.androidABI is None or self.osType == OSType.ANDROID
        self.androidDevice = kwargs.pop('androidDevice', None)
        self.compiler = kwargs.pop('compiler', None)
        self.is64 = kwargs.pop('is64', True if self.osType in [OSType.WINDOWS, OSType.LINUX] else None)
        self.buildShared = kwargs.pop('buildShared', True)
        assert not (self.buildShared is None)
        self.isPrecommit = kwargs.pop('isPrecommit', False)
        self.isPerf = kwargs.pop('isPerf', False)
        self.envCmd = kwargs.pop('envCmd', "buildenv")
        self.env = kwargs.pop('env', {}).copy()
        assert type(self.env) is dict
        self.cmake_generator = kwargs.pop('cmake_generator', None)

        if not hasattr(self, 'useCategory'):
            self.useCategory = kwargs.pop('useCategory', None)

        assert len(kwargs.keys()) == 0, 'Unknown parameters: ' + ' '.join(kwargs.keys())

        self.r_warning_pattern = re.compile(r'.*warning[: ].*', re.I | re.S)

        if self.useSlave is None:
            if self.platform == 'default':
                if self.osType == OSType.LINUX:
                    if self.is64:
                        self.useSlave = ['linux-slave-x64']
                elif self.osType == OSType.WINDOWS:
                    self.useSlave = ['windows-slave-x64']
                elif self.osType == OSType.MACOSX:
                    self.useSlave = ['macosx-slave']
                elif self.osType == OSType.ANDROID:
                    self.useSlave = ['linux-slave-x64']


    def fillSteps(self):
        self.factorySteps = []
        self.initialize()
        self.cleanup_builddir()
        self.checkout_sources()
        self.cmake()
        self.compile()
        self.testAll()
        self.cleanup()


    def getName(self):  # derived classes should implement only name() method
        if self.builderName:
            return self.builderName
        name = self.nameprefix()
        name += self.branchSafeName if not self.isPrecommit else "precommit"
        n = self.name()
        if n and len(n) > 0:
            name += '_' + n
        name += self.getPlatformSuffix()
        name += self.getNameSuffix()
        return name


    def getPlatformSuffix(self):
        name = ""
        if self.platform and self.platform != 'default':
            name = '-' + self.platform
        if self.osType:
            name += '-' + OSType.suffix[self.osType]
            if self.osType != OSType.ANDROID:
                name += "" if self.is64 is None else ("64" if self.is64 else "32")
                if self.compiler is not None:
                    name += '-' + self.compiler
            else:
                if self.androidABI:
                    name += '-' + self.androidABI
        return name


    def codebase(self):
        if not self.isPrecommit:
            return self.branch
        return None


    def GitStep(self):
        return Git(name="Fetch code", repourl=Interpolate('%(src:code:repository)s'), workdir=self.SRC_DIR,
            haltOnFailure=True, codebase='code')


    def init_consts(self):
        assert not self.envCmd is None
        self.envCmd += ' '
        self.s_checkouts = [ self.GitStep() ]
        if self.isPrecommit:
            self.s_checkouts += [
                getMergeCommand('code', self.SRC_DIR),
            ]

        if self.osType != OSType.ANDROID:
            if self.compiler is None:
                if self.osType == OSType.WINDOWS:
                    self.compiler = 'vc12'

            if (not 'BUILD_ARCH' in self.env) and (self.is64 is not None):
                if self.is64:
                    self.env['BUILD_ARCH'] = 'x64'
                else:
                    self.env['BUILD_ARCH'] = 'x86'
            if (not 'BUILD_COMPILER' in self.env) and (self.compiler is not None):
                self.env['BUILD_COMPILER'] = self.compiler

            if self.cmake_generator is None:
                if self.compiler == 'vc10':
                    self.cmake_generator = '"Visual Studio 10 Win64"' if self.is64 else '"Visual Studio 10"'
                elif self.compiler == 'vc11':
                    self.cmake_generator = '"Visual Studio 11 Win64"' if self.is64 else '"Visual Studio 11"'
                elif self.compiler == 'vc12':
                    self.cmake_generator = '"Visual Studio 12 Win64"' if self.is64 else '"Visual Studio 12"'

        self.cmakepars = {}
        self.cmakepars['BUILD_SHARED_LIBS'] = 'ON' if self.buildShared else 'OFF'

        if self.osType == OSType.ANDROID:
            del self.cmakepars['BUILD_SHARED_LIBS']
            #self.cmakepars['CMAKE_TOOLCHAIN_FILE'] = 'android.toolchain.cmake'
            if self.androidABI:
                self.cmakepars['ANDROID_ABI'] = self.androidABI


    def initialize(self):
        class InitializeStep(BuildStep):
            def start(self):
                timestamp = datetime.datetime.now()
                prop_name = 'timestamp'
                timestamp_prop = self.getProperty(prop_name, None)
                if timestamp_prop:
                    prop_name = 'my_timestamp'
                timestamp_str = timestamp.strftime("%Y%m%d-%H%M%S")
                self.setProperty(prop_name, timestamp_str, 'Initialize Step')
                timestamp_prop = self.getProperty(prop_name, None)
                if timestamp_prop is None or timestamp_prop != timestamp_str:
                    self.finished(FAILURE)
                else:
                    self.finished(SUCCESS)

        self.factorySteps.append(InitializeStep(name='initialize',
               hideStepIf=lambda result, s: result == SUCCESS, haltOnFailure=True))

        # run buildenv with dummy command to remove Git index.lock
        self.factorySteps.append(ShellCommand(command=self.envCmd + 'echo Initialize', env={'BUILD_INITIALIZE':'1'},
            workdir='.',
            name='init', descriptionDone='init', description='init',
            haltOnFailure=True))  # , hideStepIf=lambda result, s: result == SUCCESS))



    def checkout_sources(self):
        for checkout in self.s_checkouts:
            self.factorySteps.append(checkout)


    def cleanup_builddir(self):
        self.factorySteps.append(RemoveDirectory(dir='build', hideStepIf=lambda result, s: result == SUCCESS,
                                                 haltOnFailure=True))
        self.factorySteps.append(MakeDirectory(dir='build', hideStepIf=lambda result, s: result == SUCCESS,
                                               haltOnFailure=True))

    @defer.inlineCallbacks
    def genCMakePars(self, props):
        cmakeparsEvaluated = {}
        for key, value in self.cmakepars.items():
            value = yield interpolateParameter(value, props)
            cmakeparsEvaluated[key] = value
        cmakepars = ' '.join(['-D%s=%s' % (key, value) \
            for key, value in cmakeparsEvaluated.items() if len(value) > 0])
        defer.returnValue(cmakepars)


    def cmake(self, builddir='build', cmakedir='../' + SRC_DIR):
        @renderer
        @defer.inlineCallbacks
        def cmake_command(props):
            cmakepars = yield defer.maybeDeferred(self.genCMakePars, props)
            command = self.envCmd + 'cmake'
            if self.cmake_generator:
                command += ' -G%s' % self.cmake_generator
            command += ' %s %s' % (cmakepars, cmakedir)
            defer.returnValue(command)

        self.factorySteps.append(Compile(command=cmake_command, env=self.env,
            workdir=builddir, name='cmake', haltOnFailure=True,
            descriptionDone='cmake', description='cmake',
            warningPattern=self.r_warning_pattern, warnOnWarnings=True))


    def compile(self, builddir='build', config='release', target=None, useClean=False, desc=None, doStepIf=True):
        @renderer
        def compileCommand(props):
            command = '%s cmake --build . --config %s' % (self.envCmd, config)
            if not target is None:
                command += ' --target %s' % target
            if useClean:
                command += ' --clean-first'
            cpus = props.getProperty('CPUs')
            if cpus:
                if cpus < 4:
                    n = cpus + 1
                else:
                    n = 4
                if self.compiler is None or not self.compiler.startswith('vc'):
                    command += ' -- -j%s' % n
                else:
                    command += ' -- /maxcpucount:%s' % n
            if self.osType == OSType.WINDOWS:
                command += ' /consoleloggerparameters:NoSummary'
            return command

        if desc is None:
            desc = 'compile %s' % config
        self.factorySteps.append(
            Compile(command=compileCommand, workdir=builddir, env=self.env,
                    name=desc, descriptionDone=desc, description=desc, doStepIf=doStepIf,
                    warningPattern=self.r_warning_pattern,
                    warnOnWarnings=True, haltOnFailure=True))


    def addTestsPrepareStage(self):
        if hasattr(self, 'prepareStageAdded'):
            return
        self.prepareStageAdded = True
        if self.androidABI:
            if self.androidDevice:
                desc = 'adb connect'
                self.factorySteps.append(
                    ShellCommand(command=self.envCmd + 'adb connect %s' % self.androidDevice,
                            env=self.env,
                            name=desc, descriptionDone=desc, description=desc,
                            warnOnWarnings=True, haltOnFailure=True))

    def addTests(self, builddir='build', testFilter=Interpolate('%(prop:test_filter)s'), testSuffix='',
                 haltOnFailure=True, doStepIf=True):
        if self.androidABI:
            if self.androidDevice is None:
                # No tests without device
                return

        self.addTestsPrepareStage()

        buildDesc = ''
        if builddir != 'build':
            buildDesc = '-%s' % builddir

        test = 'test'
        cmd = ('bin\\Release\\' if self.osType == OSType.WINDOWS else './bin/') + 'test'
        testPrefix = 'test'

        env = self.env.copy()

        hname = '%s_%s%s%s' % (testPrefix, test, testSuffix, buildDesc)

        #resultsFileOnSlave = 'results_%s_%s%s.xml' % (testPrefix, test, testSuffix)

        # Maximum overall time from the start before the command is killed.
        maxTime = 40 * 60 if self.isPrecommit else 60 * 60
        # Maximum time without output before the command is killed.
        timeout = 3 * 60 if self.isPrecommit else 5 * 60

        args = dict(name=hname, workdir=builddir,
                command=self.envCmd + cmd, env=env, descriptionDone=hname, description=hname,
                warnOnWarnings=True, maxTime=maxTime, timeout=timeout,
                doStepIf=doStepIf, hideStepIf=hideStepIfDefault)
        step = ShellCommand(**args)
        self.factorySteps.append(step)


    def testAll(self):

        if self.osType == OSType.ANDROID and self.androidDevice is None:
            return

        self.addTests()


    def cleanup(self):
        #self.factorySteps.append(RemoveDirectory(dir='build', hideStepIf=lambda result, s: result == SUCCESS,
        #                                         haltOnFailure=True))
        pass


    def getFactory(self):
        factory = BuildFactory()
        for step in self.factorySteps:
            if type(step) is list:
                raise Exception('Error: build step is list')
            if step is None:
                raise Exception('Error: build step is None')
            factory.addStep(step)
        return factory


    def register(self):
        self.init_consts()
        self.fillSteps()

        props = { }
        if self.platform:
            props['platform'] = self.platform
        if not self.isPrecommit and self.branch:
            props['branch'] = self.branch
        return BuilderConfig(
            name=self.getName(),
            slavenames=self.slaves(),
            factory=self.getFactory(),
            mergeRequests=False,
            category=self.useCategory if not self.isPrecommit or self.useCategory is not None else 'precommit',
            properties=props)

    #
    # Helpers
    #
    def slaves(self):
        if self.useSlave is None:
            raise Exception('implement slaves() method or pass useSlave ctor parameter')
        return [self.useSlave] if isinstance(self.useSlave, str) else self.useSlave

    def name(self):
        return self.useName

    def nameprefix(self):
        if self.useNamePrefix is None:
            return ""
        return self.useNamePrefix

    def getNameSuffix(self):
        return "" if self.buildShared else "-static"
