import os

from cuneify_interface import FileCuneiformCache, cuneify_line


def application(environ, start_response):
    ''' Entry point for the application '''
    response_body = '''<!doctype html>
<html lang="en">
<head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/></head>
<body>
{}
</body></html>'''

    cache_file_path = os.path.join(environ['OPENSHIFT_DATA_DIR'], 'cuneiform_cache.pickle')
    try:
        with FileCuneiformCache(cache_file_path=cache_file_path) as cache:
            cuneiform = cuneify_line(cache, 'd-un KESZ2', False)
        response_body = response_body.format(cuneiform)
    except Exception as exc:
        # TODO nice formatting of error to be useful to the user
        response_body = response_body.format(exc)

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

