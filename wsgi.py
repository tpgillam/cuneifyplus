import os

from cgi import parse_qs

from cuneify_interface import FileCuneiformCache, cuneify_line


MY_URL = 'https://cuneifyplus-puffin.rhcloud.com'


def _get_input_form():
    ''' Return a form that the user can use to enter some transliterated text '''
    body = '''
    <form action="{}/cuneify" method="get">
    <textarea rows="10" cols="80" name="input">Enter transliteration here...</textarea>
    <input type="submit">
    </form>'''.format(MY_URL)
    return body


def _get_cuneify_body(environ, transliteration):
    ''' Return the HTML body contents when we've been given a transliteration '''
    # We use a cache in the data directory. This isn't touched by the deployment process
    cache_file_path = os.path.join(environ['OPENSHIFT_DATA_DIR'], 'cuneiform_cache.pickle')

    body = ''
    try:
        with FileCuneiformCache(cache_file_path=cache_file_path) as cache:
            cuneiform = cuneify_line(cache, transliteration, False)
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
        try:
            transliteration = parameters['input']
        except KeyError:
            body = _get_input_form()
        else:
            body = _get_cuneify_body(environ, transliteration)
    else:
        body =  _get_input_form()


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

