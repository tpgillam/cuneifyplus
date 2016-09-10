import cgi
import os

from collections import OrderedDict
from traceback import format_exc
from urllib.parse import quote

from cuneify_interface import (FileCuneiformCache, TransliterationNotUnderstood, UnrecognisedSymbol,
                               cuneify_line, ordered_symbol_to_transliterations)


# A mapping from font name to description
FONT_NAMES = OrderedDict([
        ('Santakku', 'Cursive Old Babylonian'),
        ('CuneiformOB', 'Monumental Old Babylonian'),
        ('SantakkuM', 'Monumental Old Babylonian'),
        ('UllikummiA', 'Hittite'),
        ('UllikummiB', 'Hittite'),
        ('UllikummiC', 'Hittite'),
        ('Assurbanipal', 'Neo-Assyrian'),
        ('CuneiformNA', 'Neo-Assyrian'),
        ])

FONTS_PATH_NAME = '/fonts'
MY_URL = 'https://cuneifyplus-puffin.rhcloud.com'


def _get_input_form(initial='Enter transliteration here...'):
    ''' Return a form that the user can use to enter some transliterated text '''
    font_name_selection = ''.join(['<option value="{0}">{1} (font: {0})</option>'.format(name, description) 
                                   for name, description in FONT_NAMES.items()])
    body = '''
    <form action="{}/cuneify" method="post">
    <textarea rows="10" cols="80" name="input"></textarea>
    <br /> <br />
    <input type="checkbox" name="show_transliteration">Show transliteration with output<br /><br />
    <select name="font_name">{}</select>
    <input type="submit" name="action" value="Cuneify">
    <input type="submit" name="action" value="Symbol list">
    </form>'''.format(MY_URL, font_name_selection)
    # TODO Use 'initial' when it can be made to disappear on entry into widget
    return body


def _cache_file_path(environ):
    ''' Return the standard cuneiform cache file path '''
    # We use a cache in the data directory. This isn't touched by the deployment process
    return os.path.normpath(os.path.join(environ['OPENSHIFT_DATA_DIR'], 'cuneiform_cache.pickle'))


def _get_cuneify_body(environ, transliteration, show_transliteration, font_name):
    ''' Return the HTML body contents when we've been given a transliteration, and show in the specified font '''
    body = ''
    with FileCuneiformCache(cache_file_path=_cache_file_path(environ)) as cache:
        for line in transliteration.split('\n'):
            # Make empty lines appear as breaks in the output
            line = line.strip()
            if line == '':
                body += '<br />'
                continue

            try:
                body += '<span class="{}">{}</span><br />'.format(font_name.lower(), cuneify_line(cache, line, show_transliteration).replace('\n', '<br />'))
                # body += '{}<br />'.format(cuneify_line(cache, line, show_transliteration).replace('\n', '<br />'))
            except UnrecognisedSymbol as exception:
                body += '<font color="red">Unknown symbol "{}" in "{}"</font><br />'.format(exception.transliteration, line)
            except TransliterationNotUnderstood:
                body += '<font color="red">Possible formatting error in "{}"</font><br />'.format(line)

    # TODO will need javascript to re-populate the text area, I believe
    # body += '<br /><br /><a href="{}?input={}">Go back</a>'.format(MY_URL, quote(transliteration))
    body += '<br /><br /><a href="{}">Go back</a>'.format(MY_URL)
    # TODO this can probably be neatened up a little bit
    return body


def _get_symbol_list_body(environ, transliteration, font_name):
    ''' Return the HTML body for the symbol list page '''
    body = ''
    with FileCuneiformCache(cache_file_path=_cache_file_path(environ)) as cache:
        try:
            for cuneiform_symbol, transliterations in ordered_symbol_to_transliterations(cache, transliteration).items():
                line = '<span class="{}">{}</span>: {}<br />'.format(font_name.lower(), cuneiform_symbol, ', '.join(transliterations))
                body += line
        except (UnrecognisedSymbol, TransliterationNotUnderstood):
            # In the event of an exception, show the normal cuneification,
            # including the transliteration
            body += 'There was an error - see below<br /><br />'
            body += _get_cuneify_body(environ, transliteration, True, font_name)
            return body

    # TODO will need javascript to re-populate the text area, I believe
    # body += '<br /><br /><a href="{}?input={}">Go back</a>'.format(MY_URL, quote(transliteration))
    body += '<br /><br /><a href="{}">Go back</a>'.format(MY_URL)
    # TODO this can probably be neatened up a little bit
    return body


def construct_font_response(environ, start_response, path_info):
    ''' Given a requested path, construct a response with the data from the requested font file '''
    font_directory = os.path.join(environ['OPENSHIFT_DATA_DIR'], 'fonts') 

    font_path = os.path.normpath(path_info.replace(FONTS_PATH_NAME, font_directory))

    if not font_path.startswith(font_directory):
        raise RuntimeError("Requesting font {} that is not in fonts directory {}".format(font_path, font_directory))

    # The response body is just what we get from reading the font.
    # TODO we could cache this in memory if reading the font is slow
    with open(font_path, 'rb') as f:
        response_body = f.read()
     
    status = '200 OK'
    if font_path.endswith('.woff'):
        ctype = 'application/x-font-woff'
    elif font_path.endswith('.eot'):
        ctype = 'application/vnd.ms-fontobject'
    elif font_path.endswith('.ttf'):
        ctype = 'application/x-font-ttf'

    response_headers = [('Content-Type', ctype), ('Content-Length', str(len(response_body)))]
    start_response(status, response_headers)
    return [response_body]


def application(environ, start_response):
    ''' Entry point for the application '''
    # Use the appropriate behaviour here
    path_info = environ['PATH_INFO']
    form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ, keep_blank_values=True)
    if path_info.startswith(FONTS_PATH_NAME):
        # Return the static font file
        return construct_font_response(environ, start_response, path_info)
    elif path_info == '/cuneify':

        # Whatever else happens, we always need a non-empty transliteration
        transliteration = form.getvalue('input')
        if transliteration is None or transliteration == '':
            # There is no transliteration, so show the input form again
            body = _get_input_form()

        # Get the values of the other form inputs
        show_transliteration_value = form.getvalue('show_transliteration')
        show_transliteration = show_transliteration_value is not None and show_transliteration_value.lower() == 'on'
        font_name = form.getvalue('font_name')
        action_value = form.getvalue('action')

        # The type of form submission we make determines what we do now
        if action_value == 'Cuneify':
            # We do a transliteration and show the output
            body = _get_cuneify_body(environ, transliteration, show_transliteration, font_name)
        elif action_value == 'Symbol list':
            # Make a symbol list!
            body = _get_symbol_list_body(environ, transliteration, font_name)
        else:
            raise RuntimeError("Unrecognised action value {}".format(action_value))
    else:
        body =  _get_input_form()

    # All the CSS representing font classes
    font_info = '\n'.join(['''@font-face {{{{
    font-family: {1};
    src: url(fonts/{1}.woff) format('woff'),
         url(fonts/{1}.eot) format('embedded-opentype'),
         url(fonts/{1}.ttf) format('truetype');
}}}}
.{0} {{{{
    font-family: {1};
}}}}'''.format(font_name.lower(), font_name) for font_name in FONT_NAMES])

    response_body = '''<!doctype html>
<html lang="en">
<head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<style>''' + font_info + '''</style>
</head>
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

