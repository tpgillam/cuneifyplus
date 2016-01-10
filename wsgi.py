from cuneify_interface import FileCuneiformCache, cuneify_line


def application(environ, start_response):
    ''' Entry point for the application '''
    response_body = 'hello'
    raise ValueError
    # with FileCuneiformCache(cache_file_path='cuneiform_cache.pickle') as cache:
    #     response_body =+ cuneify_line(cache, 'd-un KEZ2')
    response_body = response_body.encode('utf-8')

    status = '200 OK'
    ctype = 'text/plain'
    # ctype = 'text/html'
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

