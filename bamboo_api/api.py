"""
This module contains the BambooAPIClient, used for communicating with the
Bamboo server web service API.
"""

from inspect import getmembers
from pprint import pprint
from bs4 import BeautifulSoup
from lxml import html

import os
import requests


class BambooAPIClient(object):
    """
    Adapter for Bamboo's web service API.
    """
    # Default host is local
    DEFAULTlHOST = 'http://localhost'
    DEFAULT_PORT = 8085

    # Endpoints
    API_PREFIX = '/rest/api/latest'

    PROJECTS_SERVICE = API_PREFIX + '/project'
    PROJECT_SERVICE = API_PREFIX + '/project/{projectKey}'
    PROJECT_CREATE = '/project/saveNewProject.action'
    PROJECT_PERMISSION_GROUP = API_PREFIX + '/permissions/project/{projectKey}/groups/{groupName}'

    USERGROUP_CREATE = '/admin/group/createGroup.action'
    USERGROUP_CHANGEUSER = '/admin/group/updateGroup.action'

    REPO_LIST = '/admin/configureLinkedRepositories!doDefault.action'
    REPO_ADD = '/admin/createLinkedRepository.action'
    REPO_SEARCH_STASH = '/rest/stash/latest/projects/repositories'
    REPO_SEARCH_STASH_BRANCHES = '/rest/stash/latest/projects/repositories/branches'

    BUILD_SERVICE = API_PREFIX + '/result'
    DEPLOY_SERVICE = API_PREFIX + '/deploy/project'
    ENVIRONMENT_SERVICE = API_PREFIX + '/deploy/environment/{env_id}/results'
    PLAN_SERVICE = API_PREFIX + '/plan'
    QUEUE_SERVICE = API_PREFIX + '/queue'
    RESULT_SERVICE = API_PREFIX + '/result'
    SERVER_SERVICE = API_PREFIX + '/server'
    BFL_ACTION = '/build/label/viewBuildsForLabel.action'

    BRANCH_SERVICE = PLAN_SERVICE + '/{key}/branch'
    BRANCH_RESULT_SERVICE = RESULT_SERVICE + '/{key}/branch/{branch_name}'

    DELETE_ACTION = '/chain/admin/deleteChain!doDelete.action'




    def __init__(self, host=None, port=None, user=None, password=None, prefix='', verify=True, cert=None, url=None ):
        """
        Set connection and auth information (if user+password were provided).
        """
        self._session = requests.Session()
        self._session.verify = verify

        if url:
          self._host = None
          self._port = None
          self._prefix = None
          self._url = url

        else:
          self._host = host or self.DEFAULT_HOST
          self._port = port or self.DEFAULT_PORT
          self._prefix = prefix
          self._url = None
          
        if user and password:
            self._session.auth = (user, password)

        if cert:
          self._session.cert = cert
          

    def _get_response(self, path, params=None, headers=None):
        """
        Make the call to the service with the given queryset and whatever params
        were set initially (auth).
        """
        res = self._session.get(self._make_url(path), params=params or {}, headers=headers or {'Accept': 'application/json'})
        #if res.status_code != 200:
            #raise Exception(res)
        return res


    def _post_response(self, path, params=None, data=None, headers=None):
        """
        Post to the service with the given queryset and whatever params
        were set initially (auth).
        """
        res = self._session.post(self._make_url(path), params=params or {}, headers=headers or {'Accept': 'application/json'}, data=data or {})
        #if res.status_code != 200:
            #raise Exception(res.reason)
        return res


    def _put_response(self, path, params=None, data=None, json=None, headers=None):
        """
        PUT to the service with the given queryset and whatever params
        were set initially (auth).
        """
        res = self._session.put(self._make_url(path), params=params or {}, headers=headers or {'Accept': 'application/json'}, data=data or {}, json=json)

        if res.status_code == 204:
            return True

        if res.status_code == 304:
            return False

        #raise Exception(res)
        return res


    def _make_url(self, endpoint):
        """
        Get full url string for host, port and given endpoint.

        :param endpoint: path to service endpoint
        :return: full url to make request
        """
        if endpoint[0] != '/':
            endpoint = "/{}".format(endpoint)

        if self._url:
            return '{}{}'.format(self._url, endpoint)

        return '{}:{}{}{}'.format(self._host, self._port, self._prefix, endpoint)



    def _build_expand(self, expand):
        valid_expands = set(['artifacts',
                             'comments',
                             'labels',
                             'jiraIssues',
                             'stages',
                             'stages.stage',
                             'stages.stage.results',
                             'stages.stage.results.result'])
        expands = map(lambda x: '.'.join(['results.result', x]),
                      set(expand) & valid_expands)
        return ','.join(expands)



    def build_get_by_label(self, labels=None):
        """
        Get the master/branch builds in the Bamboo server via viewBuildsForLabel.action
        - No REST API for this: https://jira.atlassian.com/browse/BAM-18428
        - Scrape https://bamboo/build/label/viewBuildsForLabel.action?pageIndex=2&pageSize=50&labelName=foo
        Simple response API dict projectKey, planKey and buildKey

        :param labels: [str]
        :return: Generator
        """

        # Until BAM-18428, call the UI
        path = self.BFL_ACTION
        qs = {}

        # Cannot search multiple labels in a single shot,
        # so iterate search - caller should de-dupe.
        for label in labels:
            qs['labelName'] = label

            # Cycle through paged results
            page_index = 1
            while 1:
                qs['pageIndex'] = page_index

                response = self._get_response(path, qs)

                # Build links are clustered in three inside a td containing a
                # span with build indicator icons.
                soup = BeautifulSoup(response.text, 'html.parser')
                for span in soup.find_all('span', {'class': ['aui-icon', 'aui-icon-small']}):
                    cell = span.find_parent('td')
                    if cell is not None and len(cell):
                        prj, plan, build = cell.find_all('a')[:3]

                        yield {'projectKey': os.path.basename(prj['href']),
                               'planKey': os.path.basename(plan['href']),
                               'buildKey': os.path.basename(build['href'])}

                # XXX rather than deconstruct the href, we advance our own
                # qs{pageIndex} until there are no more nextLinks
                page_index += 1
                nl = soup.find('a', {'class': ['nextLink']})
                if nl is None:
                    break


    def build_get_list(self, key=None, labels=None, expand=None, max_result=25, start_index=0):
        """
        Get the builds in the Bamboo server.

        :param key: str
        :param labels: list str
        :param expand: list str
        :param max_results: int, default 25
        :param start_index: int, default 0
        :return: Generator
        """
        # Build starting qs params
        qs = {'max-result': max_result, 'start-index': start_index}
        if expand:
            qs['expand'] = self._build_expand(expand)
        if labels:
            qs['label'] = ','.join(labels)

        # Get url
        if planKey:
            # All builds for one plan
            path = '{}/{}'.format(self.BUILD_SERVICE, planKey)
        else:
            # Latest build for all plans
            path = self.BUILD_SERVICE

        # Cycle through paged results
        size = 1
        while size:
            # Get page, update page and size
            response = self._get_response(path, qs).json()
            results = response['results']
            size = results['size']

            # Check if start index was reset
            # Note: see https://github.com/liocuevas/python-bamboo-api/issues/6
            if results['start-index'] < qs['start-index']:
                # Not the page we wanted, abort
                break

            # Yield results
            for r in results['result']:
                yield r

            # Update paging info
            # Note: do this here to keep it current with yields
            qs['start-index'] += size



    def deployment_get(self, projectKey=None):
        """
        Returns the list of deployment projects set up on the Bamboo server.
        :param projectKey: str
        :return: Generator
        """
        path = "{}/{}".format(self.DEPLOY_SERVICE, projectKey or 'all')
        response = self._get_response(path)
        response.raise_for_status()

        for r in response.json():
            yield r



    def environment_get_results(self, environment_id, max_result=25, start_index=0):
        """
        Returns the list of environment results.
        :param environment_id: int
        :param max_results: int, default 25
        :param start_index: int, default 0
        :return: Generator
        """
        # Build starting qs params
        qs = {'max-result': max_result, 'start-index': start_index}

        # Get url for results
        path = self.ENVIRONMENT_SERVICE.format(env_id=environment_id)

        # Cycle through paged results
        size = 1
        while qs['start-index'] < size:
            # Get page, update page size and yield results
            response = self._get_response(path, qs)
            response.raise_for_status()
            size = response.json()['size']
            for r in response['results'].json():
                yield r

            # Update paging info
            # Note: do this here to keep it current with yields
            qs['start-index'] += response['max-result']


    def plan_get_list(self, expand=None, max_result=25, start_index=0):
        """
        Return all the plans in a Bamboo server.

        :return: generator of plans
        """
        # Build starting qs params
        qs = {'max-result': max_result, 'start-index': start_index}
        if expand:
            qs['expand'] = self._build_expand(expand)

        # Get url for results
        path = self.PLAN_SERVICE

        # Cycle through paged results
        size = 1
        while qs['start-index'] < size:
            # Get page, update page size and yield plans
            response = self._get_response(path, qs).json()
            plans = response['plans']
            size = plans['size']
            for r in plans['plan']:
                yield r

            # Update paging info
            # Note: do this here to keep it current with yields
            qs['start-index'] += plans['max-result']


    def plan_get_branches(self, planKey, enabled_only=False, max_result=25, start_index=0):
        """
        Return all branches in a plan.

        :param planKey: str
        :param enabled_only: bool
        :param max_results: int, default 25
        :param start_index: int, default 0

        :return: Generator
        """
        # Build qs params
        qs = {'max-result': max_result, 'start-index': start_index}
        if enabled_only:
            qs['enabledOnly'] = 'true'

        # Get url for results
        path = self.BRANCH_SERVICE.format(key=planKey)

        # Cycle through paged results
        size = 1
        while qs['start-index'] < size:
            # Get page, update page size and yield branches
            response = self._get_response(path, qs).json()
            branches = response['branches']
            size = branches['size']
            for r in branches['branch']:
                yield r

            # Update paging info
            # Note: do this here to keep it current with yields
            qs['start-index'] += branches['max-result']


    def plan_delete(self, buildKey):
        """
        Delete a plan or plan branch with its key.

        :param buildKey: str

        :return: dict Response
        """
        # Build qs params
        # qs = {}

        # Get url
        path = self.DELETE_ACTION

        # Build Data Object
        data = {'buildKey': buildKey}

        r = self._post_response(path, data=data)
        r.raise_for_status()


    def queue_build(self, planKey, build_vars={}):
        """
        Queue a build for building

        :param planKey: str
        :param build_vars: dict
        """
        path = "{}/{}".format(self.QUEUE_SERVICE, planKey)

        # Custom builds
        qs = {}
        for k, v in build_vars.items():
            qs_k = 'bamboo.variable.{}'.format(k)
            qs[qs_k] = v

        return self._post_response(path, qs).json()


    def queue_get_list(self):
        """
        List all builds currently in the Queue
        """
        path = self.QUEUE_SERVICE
        return self._get_response(path).json()



    def build_get_results(self, planKey=None, build_number=None, expand=None, max_result=25, start_index=0):
        """
        Returns a list of results for builds
        :param planKey: str
        :param build_number: str
        :param max_results: int, default 25
        :param start_index: int, default 0
        :return: Generator
        """
        # Build qs params
        qs = {'max-result': max_result, 'start-index': start_index}
        if expand:
            qs['expand'] = self._build_expand(expand)

        if build_number is not None and planKey is not None:
            planKey = planKey + '-' + build_number
        path = "{}/{}".format(self.RESULT_SERVICE, planKey or 'all')

        # Cycle through paged results
        size = 1
        while qs['start-index'] < size:
            # Get page, update page size and yield branches
            response = self._get_response(path, qs).json()
            results = response['results']
            size = results['size']
            for r in results['result']:
                yield r

            # Update paging info
            # Note: do this here to keep it current with yields
            qs['start-index'] += results['max-result']



    def build_get_branch_results(self, planKey, branch_name=None, expand=None, favorite=False,
                           labels=None, issueKeys=None, include_all_states=False,
                           continuable=False, build_state=None, max_result=25, start_index=0):
        """
        Returns a list of results for plan branch builds

        :param planKey: str
        :param branch_name: str
        :param expand: list str
        :param favorite: bool
        :param labels: list
        :param issueKeys: list
        :param include_all_states: bool
        :param continuable: bool
        :param build_state: str
        :param max_results: int, default 25
        :param start_index: int, default 0

        :return: Generator
        """
        # Build qs params
        qs = {'max-result': max_result, 'start-index': start_index}
        if expand:
            qs['expand'] = self._build_expand(expand)
        if favorite:
            qs['favorite'] = True
        if labels:
            qs['label'] = ','.join(labels)
        if issueKeys:
            qs['issueKey'] = ','.join(issueKeys)
        if include_all_states:
            qs['includeAllStates'] = True
        if continuable:
            qs['continuable'] = True
        if build_state:
            valid_build_states = ('Successful', 'Failed', 'Unknown')
            if build_state not in valid_build_states:
                raise ValueError('Incorrect value for \'build_state\'. Valid values include: %s', ','.join(valid_build_states))
            qs['build_state'] = build_state

        # Get url for results
        path = self.BRANCH_RESULT_SERVICE.format(key=planKey, branch_name=branch_name)

        # Cycle through paged results
        size = 1
        while qs['start-index'] < size:
            # Get page, update page size and yield branches
            response = self._get_response(path, qs).json()
            results = response['results']
            size = results['size']
            for r in results['result']:
                yield r

            # Update paging info
            # Note: do this here to keep it current with yields
            qs['start-index'] += results['max-result']



    def project_get_list(self, max_result=25, start_index=0):
        """
        List all projects
        """
        path = self.PROJECTS_SERVICE
        qs = {'max-result': max_result, 'start-index': start_index}

        r  = self._get_response(path, qs)
        r.raise_for_status()
        return r.json()



    def project_get_by_key(self, key):
        """
        Get project Info by Key
        """
        path = self.PROJECT_SERVICE.format(projectKey=key)
        r = self._get_response(path)
        r.raise_for_status()

        return r.json()



    def isProject(self, key):
        """
        Test for project existance
        """
        try:
          self.project_get_by_key( key )
          print("Project %s was found" % key)
          return True

        except Exception as err:
          if err.response.status_code == 404:
            print("Project %s not found" % key)
            return False

        raise Exception(err)


    def project_new(self, key, name=None, description=None):
        """
        Create a new project
        """
        data = {'projectKey': key,
                'projectName': name or key,
                'projectDescription': description or 'Project for %s' % key
                }

        try:
          reply = self._post_response(self.PROJECT_CREATE, data=data)
          return True


        except Exception as err:
          pprint(err)
          pprint(getmembers(err))

          if err.args[0].status_code == 404:
            return False

          return False


    def project_permissions_by_group(self, key, group_name, create=False, admin=False):
        """
        Change permissions for Project
        """
        json = []

        if create:
          json.append('CREATE')

        if admin:
          json.append('ADMINISTRATION')

        try:
          reply = self._put_response(self.PROJECT_PERMISSION_GROUP.format(projectKey=key, groupName=group_name), json=json)
          return { 'success': True, 'changed': reply }


        except Exception as err:
          return { 'success': False, 'err': err }



    def usergroup_new(self, group_name):
        """
        Create a new user group
        """
        data = { 'groupName': group_name }

        try:
          reply = self._post_response(self.USERGROUP_CREATE, data=data)
          return True

        except Exception as err:
          pprint(err)
          pprint(getmembers(err))

          if err.args[0].status_code == 404:
            return False

          return False


    def usergroup_set_members(self, group_name, members):
        """
        Add a member to a usergroup
        """
        data = { 'groupName': group_name, 'membersInput': members }

        try:
          reply = self._post_response(self.USERGROUP_CHANGEUSER, data=data)
          return True


        except Exception as err:
          pprint(err)
          pprint(getmembers(err))

          if err.args[0].status_code == 404:
            return False

          return False



    def server_pause(self):
        """
        Pause server
        """
        path = "{}/{}".format(self.SERVER_SERVICE, "pause")
        return self._post_response(path).json()


    def server_resume(self):
        """
        Resume server
        """
        path = "{}/{}".format(self.SERVER_SERVICE, "resume")
        return self._post_response(path).json()


    def repos_get_list(self):
        """
        Get List of linked repositories
        """
        answer = self._get_response(self.REPO_LIST)
        tree = html.fromstring(answer.content)
        target = tree.xpath('//div[@id="panel-editor-list"]/ul')

        reply = []
        for item in target[0].getchildren():
          row = {}
          row['id'] = item.get('id')
          row['class'] = item.get('class')
          row['data-item-id'] = item.get('data-item-id')
          #row['description'] = item.xpath('/h3[@class="item-title"]')
          row['description'] = item.xpath('/a/h3')
          reply.append(row)

        return reply


    def repos_search_stash(self, repoID, target):
        """
        """
        #headers={'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'}
        headers=None

        #self._get_response('/admin/viewLinkedRepositoryTypes.action', headers=headers)
        #self._get_response('/admin/addLinkedRepository.action?selectedRepository=com.atlassian.bamboo.plugins.stash.atlassian-bamboo-plugin-stash:bbserver&decorator=nothing&confirm=true&_=1525206805478', headers=headers)

        # Build qs params
        qs = { 'start':0, 'limit':100 }
        qs['_'] = 1525201658128
        qs['query'] = target
        qs['serverKey'] = repoID

        # Get url
        path = self.REPO_SEARCH_STASH

        r = self._get_response(path, params=qs, headers=headers)
        r.raise_for_status()

        return r


    def repos_search_stash_branches(self, repoID, repoUrl):
        """
        """
        # Build qs params
        qs = { 'start':0, 'limit':100 }
        qs['_'] = 1525201658128
        qs['serverKey'] = repoID
        qs['repositoryUrl'] = repoUrl
        headers={'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'}

        # Get url
        path = self.REPO_SEARCH_STASH

        r = self._get_response(path, params=qs, headers=headers)
        r.raise_for_status()

        return r

  
    def repos_create_linked_stash(self, repoURL):
        """
        Link a Bitbucket repo to Bamboo

        :param repoURL: str

        :return: dict Response
        """
        # Build qs params
        qs = {}

        # Get url
        path = self.REPO_ADD
        qs['repository.stash.repositoryUrl'] = repoURL
        qs['repository.stash.repositoryUrl'] = 'ssh://git@bitbucket.grainger.com:8080/~yrxa066/ricktest.git'

        r = self._post_response(path, data=qs)
        r.raise_for_status()

        return r

        #repositoryId=0
        #selectedRepository=com.atlassian.bamboo.plugins.stash.atlassian-bamboo-plugin-stash:bbserver
        #repository.stash.server=8bdedff1-d55e-3dd3-aab2-b3f30497c741
        #repository.stash.repositoryId=223
        #repository.stash.projectKey=~XAXK047
        #repository.stash.repositorySlug=ansible-akamai-logs
        #repository.stash.repositoryUrl=ssh://git@bitbucket.grainger.com:8080/~xaxk047/ansible-akamai-logs.git
        #repository.stash.temporary.isAdmin=false
        #repository.stash.branch=development
        #checkBoxFields=repository.stash.useShallowClones
        #repository.stash.useRemoteAgentCache=true
        #checkBoxFields=repository.stash.useRemoteAgentCache
        #checkBoxFields=repository.stash.useSubmodules
        #repository.stash.commandTimeout=180
        #checkBoxFields=repository.stash.verbose.logs
        #checkBoxFields=repository.stash.fetch.whole.repository
        #checkBoxFields=repository.stash.lfs
        #repository.stash.mirror.name=Primary
        #checkBoxFields=repository.common.quietPeriod.enabled
        #repository.common.quietPeriod.period=10
        #repository.common.quietPeriod.maxRetries=5
        #filter.pattern.option=none
        #selectFields=filter.pattern.option
        #selectedWebRepositoryViewer=com.atlassian.bamboo.plugins.stash.atlassian-bamboo-plugin-stash:bbServerViewer
        #selectFields=selectedWebRepositoryViewer
        #atl_token=db82a5e28fed9dec11886a91e6ddac2d66e4c042
        #bamboo.successReturnMode=json-as-html
        #decorator=nothing

