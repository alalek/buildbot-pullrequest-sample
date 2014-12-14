import re
import pullrequest.context
from twisted.python import log
from twisted.internet import defer, reactor, task

from buildbot.process.properties import Properties

from github import GitHub

userAgent = 'BuildBot GitHub PullRequest v1.0'
githubAccessToken = '14bb6182e498548d9d77a7a9f72679721030c252' # TODO Replace this

class GitHubContext(pullrequest.context.Context):

    updatePullRequestsDelay = 30  # seconds

    name = 'GitHub Pull Requests'
    dbname = 'pullrequests_github'

    urlpath = 'pullrequests_gh'

    builders = dict(
        linux=dict(name='Linux x64', builders=['precommit_linux64'], order=100),
        windows=dict(name='Win x64', builders=['precommit_windows64'], order=200),
        win32=dict(name='Win 32', builders=['precommit_windows32'], order=250),
        macosx=dict(name='Mac', builders=['precommit_macosx'], order=300),
        android=dict(name='Android', builders=['precommit_android'], order=400),
    )

    username = 'alalek'
    repo = 'test'

    client = None

    @defer.inlineCallbacks
    def updatePullRequests(self):
        print 'Updating pull requests from GitHub...'

        if not self.client:
            self.client = GitHub(userAgent=userAgent, async=True, reuseETag=True, access_token=githubAccessToken)
        gh_pullrequests = yield self.client.repos(self.username)(self.repo).pulls.get(state='open', per_page=100)
        if self.client.status == 304:
            print "GitHub pull requests was not changed"
            defer.returnValue(None)
        elif self.client.status == 200:
            prs = []
            for gh_pullrequest in gh_pullrequests:
                pr = {}
                pr['id'] = gh_pullrequest['number']
                pr['branch'] = gh_pullrequest['base']['ref']
                pr['author'] = gh_pullrequest['user']['login']
                pr['assignee'] = gh_pullrequest['assignee']['login'] if gh_pullrequest['assignee'] else None
                pr['head_user'] = gh_pullrequest['head']['repo']['owner']['login']
                pr['head_repo'] = gh_pullrequest['head']['repo']['name']
                pr['head_branch'] = gh_pullrequest['head']['ref']
                pr['head_sha'] = gh_pullrequest['head']['sha']
                pr['title'] = gh_pullrequest['title']
                pr['description'] = gh_pullrequest['body']
                prs.append(pr)
            defer.returnValue(prs)
        raise Exception('invalid status', self.client.status)

    def getListOfAutomaticBuilders(self, pr):
        if pr.description is not None and '**WIP**' in pr.description:
            return []
        buildersList = [
            'linux',
            'windows',
            'win32',
            # 'macosx',
            # 'android'
        ]
        return buildersList

    def getBuildProperties(self, pr, b, properties, sourcestamps):
        prid = pr.prid

        properties.setProperty('branch', pr.branch, 'Pull request')
        properties.setProperty('head_sha', pr.head_sha, 'Pull request')
        properties.setProperty('pullrequest', prid, 'Pull request')
        if b.isPerf:
            regressionTestFilter = self.extractRegressionTestFilter(pr.description)
            if regressionTestFilter is not None:
                properties.setProperty('regression_test_filter', regressionTestFilter, 'Pull request')
            else:
                print 'ERROR: Can\'t schedule perf precommit build without regression test filter. Use check_regression parameter'
                defer.returnValue(False)

        if pr.description is None or '**WIP**' in pr.description:
            self.pushBuildProperty(properties, pr.description, 'test[s]?_filter[s]?', 'test_filter')

        sourcestamps.append(dict(
            codebase='code',
            repository='https://github.com/%s/%s.git' % (self.username, self.repo),
            branch=pr.branch))

        sourcestamps.append(dict(
            codebase='code_merge',
            repository='https://github.com/%s/%s.git' % (pr.head_user, pr.head_repo),
            branch=pr.head_branch,
            revision=pr.head_sha))

        return True

    def getWebAddressPullRequest(self, pr):
        return 'https://github.com/%s/%s/pull/%s' % (self.username, self.repo, pr.prid)

    def getWebAddressPerfRegressionReport(self, pr):
        return None

context = GitHubContext()
