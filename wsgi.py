import cgi
import os

from traceback import format_exc
from urllib.parse import quote

from cuneify_interface import (FileCuneiformCache, TransliterationNotUnderstood, UnrecognisedSymbol,
                               cuneify_line)


FONTS_PATH_NAME = 'fonts'
MY_URL = 'https://cuneifyplus-puffin.rhcloud.com'


def _get_input_form(initial='Enter transliteration here...'):
    ''' Return a form that the user can use to enter some transliterated text '''
    body = '''
    <form action="{}/cuneify" method="post">
    <textarea rows="10" cols="80" name="input"></textarea>
    <br /> <br />
    <input type="checkbox" name="show_transliteration">Show transliteration with output<br /><br />
    <input type="submit" value="Cuneify">
    </form>'''.format(MY_URL, initial)
    return body


def _get_cuneify_body(environ, transliteration, show_transliteration):
    ''' Return the HTML body contents when we've been given a transliteration '''
    # We use a cache in the data directory. This isn't touched by the deployment process
    cache_file_path = os.path.join(environ['OPENSHIFT_DATA_DIR'], 'cuneiform_cache.pickle')

    body = ''
    try:
        with FileCuneiformCache(cache_file_path=cache_file_path) as cache:
            for line in transliteration.split('\n'):
                try:
                    body += '{}<br />'.format(cuneify_line(cache, line, show_transliteration).replace('\n', '<br />'))
                except UnrecognisedSymbol as exception:
                    body += '<font color="red">Unknown symbol "{}" in "{}"</font><br />'.format(exception.transliteration, line)
                except TransliterationNotUnderstood:
                    body += '<font color="red">Possible formatting error in "{}"</font><br />'.format(line)

    except Exception:
        # TODO remove generic exception catching
        # nice formatting of error to be useful to the user
        body += format_exc().replace('\n', '<br />')

    # TODO will need javascript to re-populate the text area, I believe
    # body += '<br /><br /><a href="{}?input={}">Go back</a>'.format(MY_URL, quote(transliteration))
    body += '<br /><br /><a href="{}">Go back</a>'.format(MY_URL)
    # TODO this can probably be neatened up a little bit
    return body


def construct_font_response(path_info):
    ''' Given a requested path, construct a response with the data from the requested font file '''
    font_directory = os.path.join(environ['OPENSHIFT_DATA_DIR'], 'fonts') 

    font_path = os.path.normpath(path_info.replace(FONTS_PATH_NAME, font_directory))

    if not font_path.startswith(font_directory):
        raise RuntimeError("Requesting font that is not in fonts directory")

    # The response body is just what we get from reading the font.
    # TODO we could cache this in memory if reading the font is slow
    with open(font_path, 'rb') as f:
        response_body = f.read()
     
    status = '200 OK'
    # TODO if returning font other than ttf, use appropriate MIME type
    ctype = 'application/x-font-ttf'
    response_headers = [('Content-Type', ctype), ('Content-Length', str(len(response_body)))]
    start_response(status, response_headers)
    return [response_body]


def application(environ, start_response):
    ''' Entry point for the application '''
    # Use the appropriate behaviour here
    path_info = environ['PATH_INFO']
    form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ, keep_blank_values=True)
    if path_info.startswith('/' + FONTS_PATH_NAME):
        # Return the static font file
        return construct_font_response(path_info)
    elif path_info == '/cuneify':
        transliteration = form.getvalue('input')
        if transliteration is None:
            # There is no transliteration, so show the input form again
            body = _get_input_form()
        else:
            show_transliteration_value = form.getvalue('show_transliteration')
            show_transliteration = show_transliteration_value is not None and show_transliteration_value.lower() == 'on'
            body = _get_cuneify_body(environ, transliteration, show_transliteration)
    else:
        body =  _get_input_form()

    response_body = '''<!doctype html>
<html lang="en">
<head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/></head>
<body>
{}
<br />
<br />
<br />
Powered by <a href="http://oracc.museum.upenn.edu/saao/knpp/cuneiformrevealed/cuneify/">Cuneify</a>,
by Steve Tinney.
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

