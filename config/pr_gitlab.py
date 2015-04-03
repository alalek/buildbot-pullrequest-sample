import os
import re
import pullrequest.context
from twisted.python import log, failure
from twisted.internet import defer

from buildbot.process.properties import Properties

from gitlab import GitLab

userAgent = 'BuildBot GitLab PullRequest v1.1'

class GitLabContext(pullrequest.context.Context):

    updatePullRequestsDelay = 30

    name = 'GitLab Pull Requests'
    dbname = 'pullrequests_gitlab'

    urlpath = 'pullrequests_gl'

    builders = dict(
        linux=dict(name='Linux x64', builders=['precommit_linux64'], order=100),
        windows=dict(name='Win x64', builders=['precommit_windows64'], order=200),
        win32=dict(name='Win 32', builders=['precommit_windows32'], order=250),
        macosx=dict(name='Mac', builders=['precommit_macosx'], order=300),
        android=dict(name='Android', builders=['precommit_android'], order=400),
    )

    username = '' # TODO
    repo = '' # TODO


    project_id = -1  # curl --header "PRIVATE-TOKEN: xXxXxXxXxXx" "https://gitlab.itseez.com/api/v3/projects/"
    gitlab_private_token = os.environ['GITLAB_APIKEY']  # check deploy/apikeys.sh

    client = None

    @defer.inlineCallbacks
    def updatePullRequests(self):
        print 'Updating pull requests from GitLab...'

        if not self.client:
            self.client = GitLab("https://gitlab.itseez.com/api/v3", userAgent=userAgent, private_token=self.gitlab_private_token, async=True)
        pullrequests = yield self.client.projects(self.project_id).merge_requests.get(state='opened', per_page=100)
        if self.client.status == 304:
            print "GitLab merge requests are not changed"
            defer.returnValue(None)
        elif self.client.status == 200:
            projects_info = {}
            prs = []
            for pullrequest in pullrequests:
                try:
                    newAPI = False
                    pr = {}
                    if not pullrequest['state'] in ['opened', 'reopened']:
                        continue
                    pr['id'] = pullrequest['iid']
                    pr['branch'] = pullrequest['target_branch']
                    pr['author'] = pullrequest['author']['username']
                    pr['assignee'] = pullrequest['assignee']['username'] if pullrequest['assignee'] else None
                    if newAPI:
                        if not projects_info.has_key(pullrequest['source_project_id']):
                            projects_info[pullrequest['source_project_id']] = yield self.client.projects(pullrequest['source_project_id']).get()
                        pr['head_user'] = projects_info[pullrequest['source_project_id']]['owner']['username']
                        pr['head_repo'] = projects_info[pullrequest['source_project_id']]['path_with_namespace']
                    else:  # Old API
                        pr['head_user'] = self.username
                        pr['head_repo'] = '%s/%s' % (self.username, self.repo)
                    pr['head_branch'] = pullrequest['source_branch']
                    if newAPI:
                        branch_info = yield self.client.projects(pullrequest['source_project_id']).repository.branches(pullrequest['source_branch']).get()
                    else:
                        branch_info = yield self.client.projects(pullrequest['project_id']).repository.branches(pullrequest['source_branch']).get()
                    pr['head_sha'] = branch_info['commit']['id']
                    pr['title'] = pullrequest['title']
                    pr['description'] = pullrequest.get('description', pullrequest['title'])
                    if pr['description'] is None:
                        pr['description'] = ''
                    prs.append(pr)
                except:
                    f = failure.Failure()
                    log.err(f, 'while adding merge request')
                    pass
            defer.returnValue(prs)
        raise Exception('invalid status', self.client.status)


    def getListOfAutomaticBuilders(self, pr):
        if pr.description is not None and '**WIP**' in pr.description:
            return []
        buildersList = ['linux', 'windows', 'win32', 'macosx', 'android']
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
            repository='ssh://git@gitlab.itseez.com/xxx/yyy.git',
            branch=pr.branch))

        sourcestamps.append(dict(
            codebase='code_merge',
            repository='ssh://git@gitlab.itseez.com/xxx/yyy.git',
            branch=pr.head_branch,
            revision=pr.head_sha))

        return True

    def getWebAddressPullRequest(self, pr):
        return 'https://gitlab.itseez.com/xxx/yyy/merge_requests/%d' % (pr.prid)

    def getWebAddressPerfRegressionReport(self, pr):
        return None


context = GitLabContext()
