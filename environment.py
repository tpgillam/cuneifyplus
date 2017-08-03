''' Environment-specific commands '''

import os
import socket


if 'mws' in socket.gethostname().lower():
    # Running in MWS
    MY_URL = 'http://cuneifyplus.arch.cam.ac.uk'

    def get_font_directory(environ):
        return os.path.join(environ['DOCUMENT_ROOT'], 'cuneifyplus', 'fonts')

    def cache_file_path(environ):
        ''' Return the standard cuneiform cache file path '''
        return os.path.normpath(os.path.join(environ['DOCUMENT_ROOT'], 'cuneifyplus', 'cuneiform_cache.pickle'))


else:
    # Running on OpenShift
    MY_URL = 'https://cuneifyplus-puffin.rhcloud.com'

    def get_font_directory(environ):
        return os.path.join(environ['OPENSHIFT_DATA_DIR'], 'fonts') 

    def cache_file_path(environ):
        ''' Return the standard cuneiform cache file path '''
        # We use a cache in the data directory. This isn't touched by the deployment process
        return os.path.normpath(os.path.join(environ['OPENSHIFT_DATA_DIR'], 'cuneiform_cache.pickle'))
