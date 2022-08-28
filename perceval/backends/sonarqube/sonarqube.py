# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2019 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, 51 Franklin Street, Fifth Floor, Boston, MA 02110-1335, USA.
#
# Authors:
#     Assad Montasser <assad.montasser@ow2.org>
#     Valerio Cosentino <valcos@bitergia.com>
#     Igor Zubiaurre <izubiaurre@bitergia.com>
#

import configparser                   # common usage.
import json
import logging
import os                             # for read_file().

from grimoirelab_toolkit.datetime import (datetime_to_utc,
                                          datetime_utcnow)
from grimoirelab_toolkit.uris import urijoin

from ...backend import (Backend,
                        BackendCommand,
                        BackendCommandArgumentParser,
                        uuid)
from ...client import HttpClient
from ...utils import DEFAULT_DATETIME

CONFIGURATION_FILE = 'perceval/backends/sonarqube/sonarqube.cfg'
DEFAULT_CATEGORY = 'measures'

SONAR_URL = "https://sonarcloud.io/"

# Range before sleeping until rate limit reset
MIN_RATE_LIMIT = 10
MAX_RATE_LIMIT = 500

PER_PAGE = 100

# Default sleep time and retries to deal with connection/server problems
DEFAULT_SLEEP_TIME = 1
MAX_RETRIES = 5

# For the moment static but should be either parameter, either remove
# list parameter

logger = logging.getLogger(__name__)

def read_file(filename, mode='r'):
    '''Taken from test_gitlab.

    Pending: 1. remove (import instead)  when integrated with perceval.
             2. ask for it to be moved to a common place.
    '''
    with open(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), filename), mode) as f:
        content = f.read()
    return content




class Sonar(Backend):
    """Sonarqube backend for Perceval.

    This class allows to fetch data from Sonarqube.
    See specs commented at parent class.

    :param component: Sonar component (ie project)
    :param base_url: Sonar URL in enterprise edition case;
        when no value is set the backend will be fetch the data
        from the Sonar public site.
    :param tag: label used to mark the data
    :param archive: archive to store/retrieve items
    """
    version = '0.3.0'

    CATEGORIES = ('metric', 'measures', 'history')

    def __init__(self, component, base_url=SONAR_URL, tag=None, archive=None):
        if not component:
            raise MandatoryArgumentMissig('a component.')
        origin = urijoin(base_url, 'api/')

        super().__init__(origin, tag=tag, archive=archive)
        self.base_url = base_url
        self.component = component
        self.client = SonarClient(component, base_url=base_url, archive=archive)

    def fetch(self, **kwargs):
        """Fetch the metrics from the component.

        The method retrieves, from a Sonarqube instance, the metrics
        updated since the given date.

        :param kwargs: backend arguments

        :returns: a generator of metrics
        """
        try:
            from_date = kwargs['from_date']
        except KeyError as ke:
            from_date = DEFAULT_DATETIME
        from_date = datetime_to_utc(from_date)
        kwargs['from_date'] = from_date

        try:
            category = kwargs['category']
            del kwargs['category']
        except KeyError as ke:
            category = DEFAULT_CATEGORY

        items = super().fetch(category, **kwargs)

        return items

    def fetch_items(self, category, **kwargs):
        """Fetch the metrics

        :param category: the category of items to fetch
        :param kwargs: backend arguments

        :returns: a generator of items
        """
        if category == 'metric':
            return self._fetch_metrics(**kwargs)
        elif category == 'measures':
            return self._fetch_measures(**kwargs)
        elif category == 'history':
            return self._fetch_history(**kwargs)
        else:
            raise NotImplementedError

    def _fetch_metrics(self, **kwargs):
        """Fetch enabled metric keys"""

        nmetrics = 0
        fetched_on = datetime_utcnow().timestamp()
        aux = self.client.metrics_configured_on_server()

        for metric in aux['metrics']:
            metric['fetched_on'] = fetched_on

            yield metric
            nmetrics += 1

        logger.info("Fetch process completed: %s metric keys fetched", nmetrics)

    def _fetch_measures(self, **kwargs):
        """Fetch current metric values"""
        try:
            _ = kwargs['from_date']
        except KeyError as ke:
            kwargs['from_date'] = DEFAULT_DATETIME

        nmetrics = 0
        fetched_on = datetime_utcnow().timestamp()
        component_metrics_raw = self.client.measures(**kwargs)

        component = component_metrics_raw['component']
        for metric in component['measures']:

            id_args = [component['key'], metric['metric'], str(fetched_on)]
            metric['id'] = uuid(*id_args)
            metric['fetched_on'] = fetched_on

            yield metric
            nmetrics += 1

        logger.info("Fetch process completed: %s metrics fetched", nmetrics)

    def _fetch_history(self, **kwargs):
        """Fetch current metric values"""
        try:
            _ = kwargs['from_date']
        except KeyError as ke:
            kwargs['from_date'] = DEFAULT_DATETIME

        nmetrics = 0
        fetched_on = datetime_utcnow().timestamp()

        histories = self.client.history(**kwargs)
        for metric, history in histories.items():
            for measure in history:
                id_args = [self.component, metric, measure['date']]
                yield {
                    'id': uuid(*id_args),
                    'metric': metric,
                    'value': measure['value'],
                    'measured_on': measure['date'],
                    'fetched_on': fetched_on
                }
            nmetrics += 1

        logger.info("Fetch process completed: histories for %s metrics fetched", nmetrics)

    @classmethod
    def has_archiving(cls):
        """Returns whether it supports archiving items on the fetch process.

        :returns: this backend supports items archive
        """
        return True

    @classmethod
    def has_resuming(cls):
        """Returns whether it supports to resume the fetch process.

        :returns: this backend does not support items resuming
        """
        return True

    @staticmethod
    def metadata_id(item):
        """Extracts the identifier from a Sonarqube item."""

        return str(item['id'])

    @staticmethod
    def metadata_updated_on(item):
        """Extracts the update time from a Sonarqube item.

        The timestamp is based on the current time when the metric was extracted.
        This field is not part of the data provided by Sonarqube API. It is added
        by this backend.

        :param item: item generated by the backend

        :returns: a UNIX timestamp
        """
        return item['fetched_on']

    @staticmethod
    def metadata_category(item):
        """Extracts the category from a Sonarqube item."""
        METRIC_KEY = ('key', 'type', 'name', 'description', 'domain', 'direction', 'qualitative', 'hidden', 'custom')
        CURRENT_METRIC = ('metric', 'value', 'bestValue')

        if all(key in item.keys() for key in (METRIC_KEY)):
            return 'metric'
        elif all(key in item.keys() for key in (CURRENT_METRIC)):
            return 'measures'
        else:
            return 'history'

    def _init_client(self, from_archive=False):
        """Init client"""

        return SonarClient(self.component, self.base_url, self.archive, from_archive)


class SonarClient(HttpClient):
    """Client for retrieving information from Sonarqube API

    :param component: Sonar component (ie project)
    :param base_url: Sonar URL in enterprise edition case;
        when no value is set the backend will be fetch the data
        from the Sonar public site.
    :param archive: archive to store/retrieve items
    """

    RATE_LIMIT_HEADER = "RateLimit-Remaining"
    RATE_LIMIT_RESET_HEADER = "RateLimit-Reset"

    _users = {}       # users cache

    def __init__(self, component, base_url=SONAR_URL, archive=None, from_archive=False):
        self.component = component
        base_url = urijoin(base_url, 'api')

        super().__init__(base_url, sleep_time=DEFAULT_DATETIME, max_retries=MAX_RETRIES,
                         archive=archive, from_archive=from_archive)

    def _sloppy_fix(self, response):
        """Sloppy fix.

        Something is wrong reading stored responses. The last character doesn't load.
        Tried to reduce the leading hexadecimal counter but failed.
        """
        fixed = json.loads( response.text + '}' )
        return fixed

    def metric_keys_configured_on_client(self):
        """Get list of metric keys configured for the client.

        :returns: a list of metrics
        """
        config = configparser.RawConfigParser()
        config.read( CONFIGURATION_FILE )
        metric_list = config.get( 'sonarqube' , 'TARGET_METRIC_FIELDS' )
        return metric_list.split(',')

    def metrics_configured_on_server(self):
        """Get list of metric keys enabled on the Sonarqube instance.

        :returns: a generator of metric keys
        """
        endpoint = self.base_url + '/metrics/search'
        response = super().fetch(endpoint)
        return self._sloppy_fix(response) 

    def measures(self, **kwargs):
        """Get metrics for a given component.

        :param from_date: obtain metrics updated since this date. Not implemented yet.
        :returns: a generator of metrics
        """
        try:
            metricKeys = kwargs['metricKeys']
        except KeyError as ke:
            metricKeys = ','.join(self.metric_keys_configured_on_client())
        metricKeys = metricKeys.replace(',', '%2C')
        endpoint = '{b}/measures/component?component={c}&metricKeys={k}'
        endpoint = endpoint.format(b=self.base_url, c=self.component, k=metricKeys)

        response = super().fetch(endpoint)
        return self._sloppy_fix(response)

    def history(self, **kwargs):
        """Get histories of metrics for a given component.

        :param from_date: obtain metrics updated since this date. Not implemented yet.
        :returns: a generator of measures
        """
        fetch = super().fetch
        PAGE_SIZE=20

        def _format(measures):
            '''Formats the histories of measures for easier accumulation.'''
            output = {}
            for metric in measures:
                key = metric['metric']
                output[key] = metric['history']
            return output

        def _get_page(page):
            pager = '&ps={s}&p={p}'.format(s=PAGE_SIZE,p=page) if page > 1 else ''
            response = fetch(endpoint + pager)
            aux = self._sloppy_fix(response)
            response.close()
            return aux['paging'], _format(aux['measures'])

        try:
            metricKeys = kwargs['metricKeys']
        except KeyError as ke:
            metricKeys = ','.join(self.metric_keys_configured_on_client())
        metricKeys = metricKeys.replace(',', '%2C')
        endpoint = '{b}/measures/search_history?component={c}&metrics={k}'
        endpoint = endpoint.format(b=self.base_url, c=self.component, k=metricKeys)

        page = 1
        paging, output = _get_page(page)
        while paging['pageIndex'] * paging['pageSize'] < paging['total']:
            page = page + 1
            paging, chunk = _get_page(page)
            for metric, history in chunk.items():
                output[metric].extend(history)

        return output


class SonarCommand(BackendCommand):
    """Class to run Sonaqube backend from the command line."""

    BACKEND = Sonar

    @classmethod
    def setup_cmd_parser(cls):
        """Returns the Sonarqube argument parser."""

        parser = BackendCommandArgumentParser(cls.BACKEND,
                                              from_date=True,
                                              archive=True)

        # Sonarqube options
        group = parser.parser.add_argument_group('Sonarqube arguments')
        group.add_argument('--base-url', dest='base_url',
                           help="Base URL for Sonarqube instance")

        # Positional arguments
        parser.parser.add_argument('component',
                                   help="Sonarqube component/project")

        return parser


class UsageError(Exception):
    '''Abstract exception for marking exceptions caused by wrong usage.'''
    def __init__(self, message=''):
        super().__init__( message )


class MandatoryArgumentMissig( UsageError ):
    '''A call was made missing a mandatory argument.'''
    def __init__(self, details=''):
        ERR_MESSAGE = 'Tried to init a SonarClient without {}'
        if details:
            super().__init__( ERR_MESSAGE.format(details) )
