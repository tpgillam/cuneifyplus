''' Environment-specific commands '''

import os
import socket

from cuneify_interface import FileCuneiformCache, MySQLCuneiformCache


if 'mws' in socket.gethostname().lower():
    # Running in MWS

    MY_URL = 'http://cuneifyplus.arch.cam.ac.uk'

    # TODO Remove temporary workaround whilst migrating from OpenShift to Cambridge University server
    DEPRECATED = False

    def get_font_directory(environ):
        return os.path.join(environ['DOCUMENT_ROOT'], 'cuneifyplus', 'fonts')

    def get_cache(environ):
        ''' Return the standard cuneiform cache '''
        # username: cuneify
        # password: puffin
        # dbname: cuneify
        # table: lookup   - (id, stuff). Latter is a BLOB type. Idea is that it will contain one row
        # return MySQLCuneiformCache('localhost', 'cuneify', 'puffin', 'cuneify')

        cache_file_path = os.path.normpath(os.path.join(environ['DOCUMENT_ROOT'], 'cuneifyplus',
            'cuneiform_cache.pickle'))
        return FileCuneiformCache(cache_file_path=cache_file_path, read_only=True)


else:
    # Running on OpenShift

    MY_URL = 'https://cuneifyplus-puffin.rhcloud.com'

    DEPRECATED = True

    def get_font_directory(environ):
        return os.path.join(environ['OPENSHIFT_DATA_DIR'], 'fonts')

    def get_cache(environ):
        ''' Return the standard cuneiform cache '''
        # We use a cache in the data directory. This isn't touched by the deployment process
        cache_file_path = os.path.normpath(os.path.join(environ['OPENSHIFT_DATA_DIR'], 'cuneiform_cache.pickle'))
        return FileCuneiformCache(cache_file_path=cache_file_path)
