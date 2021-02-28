""" Environment-specific commands """

import os
import socket

from cuneify_interface import FileCuneiformCache


if "mws" in socket.gethostname().lower():

    # Running in MWS
    MY_URL = "http://cuneifyplus.arch.cam.ac.uk"

    def get_font_directory(environ):
        return os.path.join(environ["DOCUMENT_ROOT"], "cuneifyplus", "fonts")

    def get_cache(environ):
        """ Return the standard cuneiform cache """
        cache_file_path = os.path.normpath(
            os.path.join(environ["DOCUMENT_ROOT"], "cuneifyplus", "cuneiform_cache.pickle")
        )
        return FileCuneiformCache(cache_file_path=cache_file_path, read_only=True)

else:

    # Running locally
    MY_URL = ""

    def get_font_directory(environ):
        return "fonts"

    def get_cache(environ):
        """ Return the standard cuneiform cache """
        # We use a cache in the data directory. This isn't touched by the deployment process
        cache_file_path = "cuneiform_cache.pickle"
        return FileCuneiformCache(cache_file_path=cache_file_path)
