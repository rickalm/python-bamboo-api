"""
This module contains the BitbucketAPIClient, used for communicating with the
Bitbucket server web service API.
"""

from inspect import getmembers
from pprint import pprint
from bs4 import BeautifulSoup
from lxml import html

import os
import requests


class BitbucketAPIClient(object):
    """
    Adapter for Bitbucket's web service API.
    """
    # Default host is local
    DEFAULTlHOST = 'http://localhost'
    DEFAULT_PORT = 8085

    # Endpoints
    PREFIX = '/rest/api/latest'
    PROJECTS_SERVICE = PREFIX + '/projects'
    PROJECT_SERVICE = PROJECTS_SERVICE + '/{projectKey}'
    PROJECT_AVATAR = PROJECTS_SERVICE + '/{projectKey}/avatar.png'

    USER = PREFIX + '/admin/users'
    GROUP = PREFIX + '/admin/groups'
    GROUP_ADD_USER = GROUP + '/add-user'
    GROUP_REMOVE_USER = GROUP + '/remove-user'



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



    def project_get_list(self, max_result=25, start_index=0):
        """
        List all projects
        """
        url = self.PROJECTS_SERVICE
        qs = {'max-result': max_result, 'start-index': start_index}
        response = self._get_response(url, qs).json()
        return response


    def project_get_by_key(self, key):
        """
        Get project Info by Key
        """
          
        url = self.PROJECT_SERVICE.format(projectKey=key)
        response = self._get_response(url)
        return response


    def isProject(self, key):
        """
        Test for project existance
        """

        try:
          self.project_get_by_key( key )
          return True

        except Exception as err:
          if err.args[0].status_code == 404:
            return False
          return None


    def group_get_by_key(self, key):
        """
        Get UserGroup Info by Key
        """
        url = self.GROUP
        qs = { 'filter': key }
        r = self._get_response(url, params=qs)
        r.raise_for_status()

        answers=filter( lambda item: item["name"] == key, r.json()['values'] )

        return answers


    def isGroup(self, key):
        """
        Test for UserGroup existance
        """

        try:
          self.group_get_by_key( key )
          return True

        except Exception as err:
          if err.args[0].status_code == 404:
            return False
          return None
