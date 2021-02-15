""" Environment-specific commands """

import os
import socket

from cuneify_interface import FileCuneiformCache, MySQLCuneiformCache


if not "mws" in socket.gethostname().lower():
    raise RuntimeError(
        "Unrecognised environment: {}".format(socket.gethostname().lower())
    )


MY_URL = "http://cuneifyplus.arch.cam.ac.uk"


def get_font_directory(environ):
    return os.path.join(environ["DOCUMENT_ROOT"], "cuneifyplus", "fonts")


def get_cache(environ):
    """ Return the standard cuneiform cache """
    # username: cuneify
    # password: puffin
    # dbname: cuneify
    # table: lookup   - (id, stuff). Latter is a BLOB type. Idea is that it will contain one row
    # return MySQLCuneiformCache('localhost', 'cuneify', 'puffin', 'cuneify')

    cache_file_path = os.path.normpath(
        os.path.join(environ["DOCUMENT_ROOT"], "cuneifyplus", "cuneiform_cache.pickle")
    )
    return FileCuneiformCache(cache_file_path=cache_file_path, read_only=True)
