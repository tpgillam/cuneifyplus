import os

from cgi import parse_qs

from cuneify_interface import FileCuneiformCache, cuneify_line


def _get_cuneify_body(environ, transliteration):
    ''' Return the HTML body contents when we've been given a transliteration '''
    # We use a cache in the data directory. This isn't touched by the deployment process
    cache_file_path = os.path.join(environ['OPENSHIFT_DATA_DIR'], 'cuneiform_cache.pickle')

    body = ''
    try:
        with FileCuneiformCache(cache_file_path=cache_file_path) as cache:
            cuneiform = cuneify_line(cache, 'd-un KESZ2', False)
        body += cuneiform
    except Exception as exc:
        # TODO nice formatting of error to be useful to the user
        body += str(exc)

    # TODO this can probably be neatened up a little bit
    return body


def application(environ, start_response):
    ''' Entry point for the application '''

    # Use the appropriate behaviour here
    path_info = environ['PATH_INFO']
    parameters = parse_qs(environ['QUERY_STRING'])
    if path_info == '/cuneify':
        body = _get_cuneify_body(parameters['input'])
    else:
        body = 'mooooo'


    response_body = '''<!doctype html>
<html lang="en">
<head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/></head>
<body>
{}
</body></html>'''


    response_body = response_body.format(body)
    response_body = response_body.encode('utf-8')

    status = '200 OK'
    # ctype = 'text/plain'
    ctype = 'text/html'
    response_headers = [('Content-Type', ctype), ('Content-Length', str(len(response_body)))]
    start_response(status, response_headers)
    return [response_body]


# Below for testing only
#
if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', 8051, application)
    # Wait for a single request, serve it and quit.
    httpd.handle_request()

