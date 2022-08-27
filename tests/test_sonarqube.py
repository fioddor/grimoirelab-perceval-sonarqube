#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Fioddor Superconcentrado
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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#
# Purpose: Automatic tests for SonarClient.
#
# Design.: - Unittest as framework.
#          - Based on taiga-20200619A.
#
# Authors:
#     Igor Zubiaurre <izubiaurre@bitergia.com>
#
# Pending:
#   - readfile shold be shared with gitlab (remove when integrating and ask for it to be moved).
#----------------------------------------------------------------------------------------------------------------------

import unittest                       # common usage.
import configparser                   # common usage.
import httpretty as mock              # for TestSonarClientAgainstMockServer.
import os
import json

import pkg_resources
pkg_resources.declare_namespace('backends')

from grimoirelab_toolkit.datetime import datetime_utcnow

# for common usage:
from perceval.backends.sonarqube.sonarqube import SonarClient
from perceval.backends.sonarqube.sonarqube import *


CFG_FILE = 'test_sonarqube.cfg'


class TestSonarCommand(unittest.TestCase):
    """SonarCommand unit tests"""


    def test_backend_class(self):
        """It's backend is the expected one."""
        self.assertIs(SonarCommand.BACKEND , Sonar)


    def test_setup_cmd_parser(self):
        """The parser object is correctly initialized."""

        TST_URL = 'https://a.sonarqube.instance'
        TST_ORI = 'a_project'

        parser = SonarCommand.setup_cmd_parser()

        # AC1:
        self.assertIsInstance(parser , BackendCommandArgumentParser)
        self.assertEqual(parser._backend , Sonar)

        # TC01: no tag:
        args = [ '--base-url', TST_URL
               , TST_ORI
               ]

        pa = parser.parse(*args)

        self.assertEqual( TST_ORI , pa.component )
        self.assertEqual( TST_URL , pa.base_url  )
        self.assertEqual( None    , pa.tag       )

        # TC02: tagged:
        TST_TAG = 'a tag'
        args = [ '--base-url'  , TST_URL
               , '--tag'       , TST_TAG
               , TST_ORI
               ]

        pa = parser.parse(*args)

        self.assertEqual( TST_ORI , pa.component )
        self.assertEqual( TST_URL , pa.base_url  )
        self.assertEqual( TST_TAG , pa.tag       )




class TestSonarBackend(unittest.TestCase):
    """Tests Backend for Sonarqube

    Pending: - Testing width:
               - test CLASSIFIED_FIELDS mechanism.
               - test Summary feature.
             - Testing depth:
               - tighter tests on retrieved data.
                 - expected type.
                 - expected value? (less maintainable).
               - make sure exceptions are raised by our own backend (or our own underlying client)
                 but not by other underlying third-party libraries.
    """


    TST_ORI = 'c01'
    TST_URL = 'https://a.sonarqube.instance/'
    TST_DBE = Sonar( TST_ORI , base_url=TST_URL )


    @classmethod
    def setUpClass(self):
        '''Shows data for testing administration.'''
        print( 'Testing Sonarqube v{}'.format( self.TST_DBE.version ) )


    def setUp(self):
        '''Sloppy fix.'''
        print() # sloppy testing fix


    def test_wrong_calls(self):
        with self.assertRaises( TypeError , msg='An empty init should have raised an Exception'):
            tsc = Sonar()
        with self.assertRaises( TypeError , msg='An init missing the component should have raised an Exception'):
            tsc = Sonar( base_url=self.TST_URL )


    def test_has_resuming(self):
        '''Expect True, but really?'''
        self.assertTrue( self.TST_DBE.has_resuming() )


    @mock.activate
    def test_fetch_items(self):
        '''Fech_items response contains expected items.

        '''

        # setup test:
        projects , expected = Utilities.mock_full_projects( self.TST_URL )

        # AC1: Unimplemented categories raise the expected exception:
        with self.assertRaises( NotImplementedError ):
            for item in self.TST_DBE.fetch_items( 'unimplemented_category', from_date='1980-01-01'):
                break

        # AC2: All mapped categories are implemented and retrieve the expected items:

        # this seems trivial, but it'll look different if not all are implemened:
        IMPLEMENTED   = set(Sonar.CATEGORIES)
        UNIMPLEMENTED = set(Sonar.CATEGORIES) - IMPLEMENTED
        self.assertEqual( 0 , len(UNIMPLEMENTED) )

        # each category that makes it through this block is implemented:
        cnt_tested = 0
        for category in IMPLEMENTED:
            # .fetch_items()[0] doesn't work
            items = self.TST_DBE.fetch_items( category, from_date='1980-01-01')
            for item in items:
                cnt_tested += 1
                # the item's category is the expected one:
                self.assertEqual( category , self.TST_DBE.metadata_category( item ) )
                break              # test only the 1st item for each category

        # makes sure no empty iterable was returned:
        self.assertEqual( len(IMPLEMENTED) , cnt_tested )


    def test_classified_fields(self):
        '''No exception raised on accessing that member.'''
        self.assertEqual( 0 , len(self.TST_DBE.CLASSIFIED_FIELDS) )


    @mock.activate
    def test_tag(self):
        '''Feched items will and can be tagged.'''
        TST_CATEGORY = 'measures'

        # test setup:
        projects , expected = Utilities.mock_full_projects( self.TST_URL )

        # AC1: will be autotagged if no tag is passed:
        for item in self.TST_DBE.fetch( category=TST_CATEGORY ):
            self.assertTrue( '01' , item[ 'tag' ] )
            break

        # AC2: will bear the input tag:
        TST_TAG = 'a tag'
        tbe = Sonar( 'c01' , base_url=self.TST_URL , tag=TST_TAG )
        for item in tbe.fetch( category=TST_CATEGORY ):
            self.assertTrue( TST_TAG , item[ 'tag' ] )
            break


    def test_categories(self):
        '''No exception raised when accessing that member.'''
        self.assertEqual( 3 , len(Sonar.CATEGORIES) )


    @mock.activate
    def test_metadata_category(self):
        '''Each item category is identified.'''

        # AC1: unknown items raise an exception:
        # with self.assertRaises( Exception ):
        #   bah = self.TST_DBE.metadata_category( {'data':{ 'unknown':'category' }} )

        # AC2: items of all categories are identified.
        projects , expected = Utilities.mock_full_projects( self.TST_URL )
        tbe = self.TST_DBE

        for category in Sonar.CATEGORIES:
            for item in tbe.fetch_items( category ):
                self.assertEqual( category , tbe.metadata_category( item ) )
                break



class TestSonarClientAgainstMockServer(unittest.TestCase):
    """Unit testing.

    Usage..: 0) Install httpretty.
             1) Run.

    Design.: + Sonarqube API client tested against a mock Sonarqube server.
               + some mock responses are read from files.
             + Setup creates a default client to be reused.

    Pending: - Complete pending test_cases. 
    """

    @classmethod
    def setUpClass(cls):
        '''Set up Sonarqube service'''


        TST_ORI = 'c01'
        cls.API_URL = 'https://a.sonarqube.instance/'
        # Default Sonarqube Client for testing:
        cls.TST_DTC = SonarClient( TST_ORI, base_url=cls.API_URL )


    def http_code_nr(self, name ):
        '''Returns an HTTP code by name.

        This is a hub function to minimize fan-out.
        '''
        return Utilities.http_code_nr( name )


    def mock_pages(self, identifier , endpoint , max_page ):
        '''Mocks paged responses.

        The page urls to mock are mapped with the endpoint. The stored responses are retrieved by identifier.
        This is a hub function to minimize fan-out. Url mapping and retrieval logic are resolved by the
            called function.
        :param: identifier: a text identier of the endpoint for retrieving the stored mock responses.
        :param: endpoint: endpoint to mock.
        :param: max_pages: number of first consecutive pages to mock for the (same) endpoint.
        '''
        Utilities.mock_pages( identifier , endpoint , max_page )


    def setUp(self):
        '''Sloppy screen fix.'''
        print()


    def test_minimial(self):
        '''Minimal test''' 

        # regular init
        tsc = SonarClient('a_component')
        self.assertTrue(isinstance(tsc, SonarClient))
        # check implicit base_url

        # empty call
        with self.assertRaises( TypeError , msg='An empty init should have raised an Exception'):
            tsc = SonarClient()


    @unittest.skip('Unauthorized is a pending test.')
    @mock.activate
    def test_no_permission(self):
        '''Sonarqube denies permission.'''

        HTTP_PERMISSION_DENIED = self.http_code_nr( 'Forbidden' )
        HTTP_UNEXPECTED        = Unexpected_HTTPcode
        def mock_url( query ):
            mock.register_uri( mock.GET
                             , self.API_URL + query
                             , status=HTTP_PERMISSION_DENIED
                             , body='''{            "etc":"etc"
                                       , "_error_message":"You do not have permission to perform this action."
                                       }
                                    '''
                             )
            #print(query)

        for u in [ 'deny' , 'projects/id' , 'projects/id/stats', 'projects/id/issues_stats' ]:
            mock_url( u )
        tc = self.TST_DTC

        # AC1: basic_rq() raises no exception:
        response = tc.basic_rq( 'deny' )
        self.assertEqual( HTTP_PERMISSION_DENIED , response.status_code )

        # AC2: everything else is paginated and rq() raises Unexpected_HTTPcode:
        with self.assertRaises( HTTP_UNEXPECTED ):
            bah = tc.rq( 'deny' )
        with self.assertRaises( HTTP_UNEXPECTED ):
            bah = tc.proj_stats( 'id' )
        with self.assertRaises( HTTP_UNEXPECTED ):
            bah = tc.proj_issues_stats( 'id' )
        with self.assertRaises( HTTP_UNEXPECTED ):
            bah = tc.proj( 'id' )
        with self.assertRaises( HTTP_UNEXPECTED ):
            bah = tc.get_lst_data_from_api( 'stats' , 'id'  )


    @unittest.skip('Wrong credentials is a pending test.')
    @mock.activate
    def test_wrong_credentials(self):
        '''Sonarqube rejects wrong token.'''

        HTTP_UNAUTHORIZED = self.http_code_nr( 'Unauthorized' )
        HTTP_UNEXPECTED   = Unexpected_HTTPcode
        def mock_url( query ):
            mock.register_uri( mock.GET
                             , self.API_URL + query
                             , status=HTTP_UNAUTHORIZED
                             , body='''{            "etc":"etc"
                                       , "_error_message": "Invalid token"
                                       , "_error_type"   : "sonarqube.base.exceptions.NotAuthenticated"
                                       }
                                    '''
                             )
            #print(query)
        for u in [ 'deny' , 'projects/id' , 'projects/id/stats', 'projects/id/issues_stats' ]:
            mock_url( u )
        tc = self.TST_DTC

        # AC1: basic_rq() raises no exception:
        response = tc.basic_rq( 'deny' )
        self.assertEqual( HTTP_UNAUTHORIZED , response.status_code )

        # AC2: everything else is paginated and rq() raises Unexpected_HTTPcode:
        with self.assertRaises( HTTP_UNEXPECTED ):
            bah = tc.rq( 'deny' )
        with self.assertRaises( HTTP_UNEXPECTED ):
            bah = tc.proj_stats( 'id' )
        with self.assertRaises( HTTP_UNEXPECTED ):
            bah = tc.proj_issues_stats( 'id' )
        with self.assertRaises( HTTP_UNEXPECTED ):
            bah = tc.proj( 'id' )
        with self.assertRaises( HTTP_UNEXPECTED ):
            bah = tc.get_lst_data_from_api( 'stats' , 'id' )


    @unittest.skip('Throttling is a pending test.')
    @mock.activate
    def test_throttling(self):
        '''Sonarqube blocks reporting throttling.'''

        def gl_now():
            ''' gets and formats current time'''
            return datetime_utcnow().replace(microsecond=0).timestamp()

        # test config:
        TST_QUERY = 'a_query'
        TST_DELAY = 2
        TST_ERROR_MSG = '{' + ''' "_error_message": "Request was throttled.Expected available in {} seconds."
                                , "_error_type"   : "sonarqube.base.exceptions.Throttled"
                              '''.format( TST_DELAY ) + '}'

        # test setup:
        mock.register_uri( mock.GET
                         , self.API_URL + TST_QUERY
                         , responses=[ mock.Response( status=self.http_code_nr( 'Too Many Requests' )
                                                    , body=TST_ERROR_MSG
                                                    )
                                     , mock.Response( status=self.http_code_nr( 'OK' )
                                                    , body='{ "content": "some_content" }'
                                                    )
                                     ]
                         )
        tc = self.TST_DTC

        # test:
        started = gl_now()
        tc.rq( TST_QUERY )
        finished = gl_now()

        # check:
        elapsed = finished - started
        self.assertLessEqual( TST_DELAY , elapsed )


    @mock.activate
    def test_metrics_configured_on_server(self):
        '''Smoke test'''

        # test config:
        TST_QUERY      = 'api/metrics/search'
        TST_PREFIX     = 'c01_metric_keys'          # Prefix of the file names containing the mocked responses.
        TST_AVAILABLE  = 1                          # Number of mocked pages available to respond the query.

        # test setup:
        TST_URL = self.API_URL + TST_QUERY
        self.mock_pages( TST_PREFIX , TST_URL , TST_AVAILABLE )

        # Smoke test
        record = self.TST_DTC.metrics_configured_on_server()

        self.assertEqual( len(record['metrics']), 100 )
        self.assertEqual( record['metrics'][0]['key'], 'new_technical_debt' )


    @mock.activate
    def test_measures(self):
        '''Smoke test

        Pending: Reenable the page limit AC.
        '''

        # test config:
        TST_QUERY      = 'api/measures/component?component=c01&metricKeys=accessors%2Cnew_technical_debt'
        TST_PREFIX     = 'c01_measures_component_2' # Prefix of the file names containing the mocked responses.
        TST_AVAILABLE  = 1                          # Number of mocked pages available to respond the query.

        # test setup:
        TST_URL = self.API_URL + TST_QUERY
        self.mock_pages( TST_PREFIX , TST_URL , TST_AVAILABLE )

        # Smoke test
        record = self.TST_DTC.measures()

        self.assertEqual( record['component']['key'], 'c01' )
        self.assertEqual( len(record['component']['measures']), 2 )

        # AC1: expect limit, if limit < available:
        #limit = TST_FULL_PAGES
        #record = self.TST_DTC.rq( TST_QUERY , limit )
        #self.assertEqual( limit * TST_PER_PAGE , len(record) )

        # AC2: expect available, if available =< limit:
        #limit = TST_AVAILABLE + TST_SOME_MORE
        #record = self.TST_DTC.rq( TST_QUERY , limit )
        #self.assertLess(        TST_FULL_PAGES * TST_PER_PAGE , len(record) )
        #self.assertGreaterEqual( TST_AVAILABLE * TST_PER_PAGE , len(record) )

        # AC3: expect available, on missing limit:
        #record = self.TST_DTC.rq( TST_QUERY )
        #self.assertLess(        TST_FULL_PAGES * TST_PER_PAGE , len(record) )
        #self.assertGreaterEqual( TST_AVAILABLE * TST_PER_PAGE , len(record) )


    @mock.activate
    def test_history(self):
        '''Smoke test

        Pending: Reenable the page limit AC.
        '''

        # test config:
        TST_QUERY      = 'api/measures/search_history?component=c01&metrics=accessors%2Cnew_technical_debt'
                                                                          #'bugs%2Ccoverage%2Ccomplexity%2Csqale_rating%2Cblocker_violations%2Ccode_smells'
        TST_PREFIX     = 'c01_history_component_6' # Prefix of the file names containing the mocked responses.
        TST_AVAILABLE  = 1                         # Number of mocked pages available to respond the query.

        # test setup:
        TST_URL = self.API_URL + TST_QUERY
        self.mock_pages( TST_PREFIX , TST_URL , TST_AVAILABLE )

        # Smoke test
        record = self.TST_DTC.history()

        self.assertEqual( record['paging']['pageIndex'], 1 )
        self.assertEqual( record['measures'][0]['metric'], 'bugs' )
        self.assertEqual( len(record['measures']), 6 )

        # AC1: expect limit, if limit < available:
        #limit = TST_FULL_PAGES
        #record = self.TST_DTC.rq( TST_QUERY , limit )
        #self.assertEqual( limit * TST_PER_PAGE , len(record) )

        # AC2: expect available, if available =< limit:
        #limit = TST_AVAILABLE + TST_SOME_MORE
        #record = self.TST_DTC.rq( TST_QUERY , limit )
        #self.assertLess(        TST_FULL_PAGES * TST_PER_PAGE , len(record) )
        #self.assertGreaterEqual( TST_AVAILABLE * TST_PER_PAGE , len(record) )

        # AC3: expect available, on missing limit:
        #record = self.TST_DTC.rq( TST_QUERY )
        #self.assertLess(        TST_FULL_PAGES * TST_PER_PAGE , len(record) )
        #self.assertGreaterEqual( TST_AVAILABLE * TST_PER_PAGE , len(record) )


class Utilities(unittest.TestCase):
    ''' Testing Utilities.'''

    def http_code( name ):
        '''Returns HTTP codes (as strings) by their name.

        Used to improve readability.
        '''
        HTTP_CODES = { '200': 'ok'
                     , '401': 'unauthorized'
                     , '403': 'forbidden'
                     , '429': 'too many requests'
                     }
        aux = name.strip().lower()
        keys = list(HTTP_CODES.keys()  )
        vals = list(HTTP_CODES.values())
        if aux in HTTP_CODES.values():
            return keys[ vals.index( aux ) ]
        else:
            return '-1'
        return

    def http_code_nr( name ):
        '''Returns HTTP codes as integers by their name.

        Used to improve readability.
        '''
        return int(Utilities.http_code( name ))

    def test_http_codes(self):
        nr = Utilities.http_code_nr
        self.assertEqual( '403' , Utilities.http_code( 'Forbidden' ) )
        self.assertEqual(  200  , Utilities.http_code_nr( 'OK'     ) )
        self.assertEqual(  200  , nr( 'OK' ) )


    def mock_pages( name , query , max_page ):
        '''Mocks a series of pages.'''
        for p in range( max_page ):
            page = p + 1

            url = query
            if 0 < p:
                url += '&page={}'.format( page )

            TST_DIR = 'data/'
            body_file = '{}{}.P{}.body.RS'.format( TST_DIR , name , page )
            head_file = '{}{}.P{}.head.RS'.format( TST_DIR , name , page )

            mock.register_uri( mock.GET , url
                             , match_querystring=True
                             ,            status=200
                             ,              body=           read_file(body_file, mode='rb')
                             ,   forcing_headers=json.loads(read_file(head_file).replace( "'" , '"' ))
                             )
            #print( 'Mock set up for {}'.format(url) )


    def mock_full_projects( api_url ):
        '''Mocks the full sequence for a list of projects.
        '''
        def mock_url( list_name , query , project , max_page ):
            name  = 'c{}_{}'.format(project , list_name )
            url   = api_url + query.format( project )
            Utilities.mock_pages( name , url , max_page )

        # config:
        #                      item ,  url cccc                                                                           , (P ,exp) , (P ,exp)
        STEPS = (
            ('measures_component_2' , 'api/measures/component?component=c{}&metricKeys=accessors%2Cnew_technical_debt'    , (1 , 2) , (1 , 2) ),
            ('metric_keys'          , 'api/metrics/search'                                                                , (1 , 2) , (1 , 2) ),
            ('history_component_6'  , 'api/measures/search_history?component=c{}&metrics=accessors%2Cnew_technical_debt'  , (1 , 2) , (1 , 2) ),
        )
        PROJECTS = ('01' , '02')

        # setup
        pn = 0
        all_sizes = {}
        for project in PROJECTS:
            pn += 1

            sizes_project = {}
            for s in STEPS:

                item = s[0]
                url  = s[1]
                page = s[1+pn][0]
                size = s[1+pn][1]

                mock_url( item , url , project , page )
                sizes_project.update( { item:size } )

            all_sizes.update( { project: sizes_project } )


        return PROJECTS , all_sizes 


    @unittest.skip('This utility runner is disabled by default. Needs a real Sonarqube.')
    def test_capture(self):
        '''Runner for testing utilities.

        Usage: adapt, enable by commenting the leading unittest.skip decorator and call
        '''
        self.capture_component_metrics_RS('api/measures/component?component=c{}&metricKeys=accessors%2Cnew_technical_debt', 'data/c01_measures_component_2.P1.PART.RS')


    def capture_pj_list_RS(self, project_id, list_name, page=None):
        '''Testing maintainance utility to capture http responses.'''

        destination = 'data/{}.P{}.PART.RS'
        url = '{}?project={}'
        if page:
            url += '&page={}'
            url = url.format( list_name , project_id , page )
            destination = destination.format( list_name , page )
        else:
            url = url.format( list_name , project_id )
            destination = destination.format( list_name , "1" )

        self.capture_basic_RS( url , destination )


    def capture_component_metrics_RS(self, url , destination):
        '''Testing maintainance utility to capture http responses.

        Captures response headers and body in respective files.
        :param destination: 'PART'-marked path to the file where to save.
                            Will create 2 files: HEAD and BODY.
        '''
        config = Utilities.read_test_config( CFG_FILE )
        sonar = SonarClient( ori=config['ori'], url=config['url']  )
        response = json.loads(sonar.component_metrics( ori ))
        if 200 == response.status_code:
            with open( destination.replace('PART' , 'head') , 'w' ) as fh:
                fh.write( str(response.headers) )
            with open( destination.replace('PART' , 'body') , 'w' ) as fb:
                fb.write( response.text )
        else:
            print( 'FAIL:'          )
            print( response.headers )
            print( response.text    )



def read_file(filename, mode='r'):
    '''Taken from test_gitlab.

    Pending: 1. remove (import instead)  when integrated with perceval.
             2. ask for it to be moved to a common place.
    '''
    with open(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), filename), mode) as f:
        content = f.read()
    return content



print( '\n' * 3 )

if __name__ == "__main__":
    print( 'Debug: Executing test_sonarqube as __main__ (called as ./script.py or as python3 script.py).' )
    print( '-' * 40 )
    unittest.main(verbosity=3)
else:
    print( 'Debug: Executing test_sonarqube as "{}".'.format(__name__) )
    print( '-' * 40 )

