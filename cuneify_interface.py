import os
import pickle
import re

from abc import ABCMeta, abstractmethod
from argparse import ArgumentParser
from collections import OrderedDict
from urllib.parse import quote, urlencode
from urllib.request import urlopen


class NotAToken(Exception):
    ''' We expected a single token, not multiple tokens '''


class TransliterationNotUnderstood(Exception):
    ''' The website didn't understand the transliteration '''


class UnrecognisedSymbol(Exception):
    ''' Indicate that the transliteration wasn't entirely converted to cuneiform '''

    def __init__(self, transliteration, *args, **argv):
        self.transliteration = transliteration
        super().__init__(*args, **argv)
        
    def __str__(self):
        return 'Unrecognised symbol in: {}'.format(self.transliteration)


# The separators between tokens. Store regex separately due to escaping of dot
TOKEN_SEPARATORS = ('-', ' ', '.')
TOKEN_REGEX = '-| |\.'


REPLACEMENT_MAP = {'š': 'sz', 
                   'ṣ': 's,', 
                   'ṭ': 't,',
                   'ĝ': 'j',
                   'ḫ': 'h',

                   # Subscripted numbers correspond to actual numbers in the original
                   '₀': '0',   
                   '₁': '1',   
                   '₂': '2',   
                   '₃': '3',   
                   '₄': '4',   
                   '₅': '5',
                   '₆': '6',
                   '₇': '7',
                   '₈': '8',
                   '₉': '9',
                   
                   # Replace 'smart' quotes with normal characters
                   '‘': "'",
                   '’': "'",
                   'ʾ': "'",
                   '“': '"',
                   '”': '"',
                   }
ACUTE_VOWELS = {'á': 'a', 'é': 'e', 'í': 'i', 'ú': 'u'}
GRAVE_VOWELS = {'à': 'a', 'è': 'e', 'ì': 'i', 'ù': 'u'}

# Extend the dictionaries at import time to include uppercase versions
REPLACEMENT_MAP.update({key.upper(): value.upper() for key, value in REPLACEMENT_MAP.items()})
ACUTE_VOWELS.update({key.upper(): value.upper() for key, value in ACUTE_VOWELS.items()})
GRAVE_VOWELS.update({key.upper(): value.upper() for key, value in GRAVE_VOWELS.items()})


def contains_ascii(byte_array, ignore_space=True):
    ''' Returns true if any character in the given bytes object is an ascii character. '''
    for character in byte_array:
        if ignore_space and character == 32:
            continue
        if character < 128:
            return True
    # Also include non-cuneiform UTF-8 symbols
    if character in REPLACEMENT_MAP or character in ACUTE_VOWELS or character in GRAVE_VOWELS:
        return True
    return False


def _remove_abbreviations(transliteration):
    ''' Remove common shorthands in tokens '''
    # Due to corrections applied here, we require that this is a token
    if any(separator in transliteration for separator in TOKEN_SEPARATORS):
        raise NotAToken()

    for original, replacement in REPLACEMENT_MAP.items():
        transliteration = transliteration.replace(original, replacement)

    # Add the number 2 to the token for acute vowels
    for original, replacement in ACUTE_VOWELS.items():
        if original in transliteration:
            transliteration += '2'
        transliteration = transliteration.replace(original, replacement)

    # Add the number 3 to the token for grave vowels
    for original, replacement in GRAVE_VOWELS.items():
        if original in transliteration:
            transliteration += '3'
        transliteration = transliteration.replace(original, replacement)
    return transliteration


def _get_cuneiform(transliteration):
    ''' Get the UTF-8 encoded cuneiform for the given transliteration string '''
    # Debugging
    # print('Looking up: "{}"'.format(transliteration))
    transliteration = _remove_abbreviations(transliteration)

    url = 'http://oracc.museum.upenn.edu/cgi-bin/cuneify'
    # TODO in python 3.5 we can use the quote_via argument to urlencode
    # values = {'input': transliteration}
    # data = urlencode(values, quote_via=quote)
    # data = 'input={}'.format(quote(transliteration.encode('utf-8')))
    data = 'input={}'.format(quote(transliteration))
    url = '{}?{}'.format(url, data)
    with urlopen(url) as response:
        html = response.read()
        match = re.search(b'"output cuneiform">(.*)</p>', html)
        if match is None:
            print("No cuneiform found for transliteration {} in result: {}".format(transliteration, html))
            raise UnrecognisedSymbol(transliteration)
        result = match.group(1)
        if result.startswith(b"Sorry, I didn\'t understand your transliteration"):
            print("Transliteration {} not understood".format(transliteration))
            raise TransliterationNotUnderstood
        if contains_ascii(result):
            raise UnrecognisedSymbol(transliteration)
        return result


class CuneiformCacheBase:
    ''' Abstract class representing a cuneiform class. It is a context manager, where the cache will be loaded 
        on entry and updated at exit.

        The public API is the get_cuneiform() method, which is given one transliteration token.
    '''

    __metaclass__ = ABCMeta

    def __init__(self):
        # These are symbols that we don't attempt to transliterate
        self._unmodified_sybols = ('x', 'X', '?', '!', '[', ']')
        self.transliteration_to_cuneiform = {}

    @abstractmethod
    def __enter__(self):
        ''' Get the current transliteration -> cuneiform map from storage '''

    @abstractmethod
    def __exit__(self, type_, value, traceback):
        ''' Update the cache with the current transliteration, cuneiform pairs. It will overwrite the given 
            values if present 
        '''

    def _get_cuneiform_bytes(self, transliteration):
        ''' Get the cuneiform bytes array corresponding to the given transliteration, using the cache if available.'''
        if transliteration not in self.transliteration_to_cuneiform:
            self.transliteration_to_cuneiform[transliteration] = _get_cuneiform(transliteration)
        return self.transliteration_to_cuneiform[transliteration]

    def get_cuneiform(self, transliteration):
        ''' Get the UTF-8 string corresponding to the cuneiform that we want '''
        # First ascertain whether it is a spcecial case, in which case don't do
        # anything
        if transliteration in self._unmodified_sybols:
            return transliteration
        return self._get_cuneiform_bytes(transliteration).decode('utf-8')


class FileCuneiformCache(CuneiformCacheBase):
    ''' Store the cuneiform cache in a pickle file '''

    def __init__(self, cache_file_path):
        self._cache_file_path = cache_file_path
        super().__init__()

    def __enter__(self):
        if os.path.isfile(self._cache_file_path):
            try:
                self._load_cache_file()
            except EOFError:
                # This probably means that the cache is corrupted. As this is a
                # proof of concept, happy to delete it
                print('{} appears to be corrupted - deleting.'.format(self._cache_file_path))
                os.remove(self._cache_file_path)
        return self

    def __exit__(self, type_, value, traceback):
        self._write_cache_file()

    def _load_cache_file(self):
        ''' Worker method to load the cache file into the local variable '''
        with open(self._cache_file_path, 'rb') as cache_file:
            stored_cache = pickle.load(cache_file)
            self.transliteration_to_cuneiform.update(stored_cache)

    def _write_cache_file(self):
        ''' Worker method to write the cache file to disk '''
        with open(self._cache_file_path, 'wb') as cache_file:
            pickle.dump(self.transliteration_to_cuneiform, cache_file)


def cuneify_line(cache, transliteration, show_transliteration):
    ''' Take a line of transliteration and display the output, nicely formatted, on the terminal.
        Should be used whilst in the context of cache. 
    '''
    transliteration = transliteration.strip()
    # Split using alphanumeric characters (\w)
    tokens = re.split(TOKEN_REGEX, transliteration)

    # It's a much easier code path if we just show the cuneiform
    if not show_transliteration:
        return ' '.join(cache.get_cuneiform(token) for token in tokens)

    # Otherwise format something like this:
    #
    # tok1.tok2  tok3-tok4-5-   6
    # A    BBBBB CC   DDD  EEEE F
    separators = re.findall(TOKEN_REGEX, transliteration)
    separators.append('')

    line_original = ''
    line_cuneiform = ''
    for token, separator in zip(tokens, separators):
        symbol = cache.get_cuneiform(token)
        # FIXME -- take into account separator length (could be more than one
        # character
        n_spaces_after_symbol = 1 + max(len(separator) + len(token) - len(symbol), 0)
        n_spaces_after_token_separator = 1 + max(len(symbol) - len(token), 0)
        line_original += token + separator + ' ' * n_spaces_after_token_separator
        line_cuneiform += symbol + ' ' * n_spaces_after_symbol

    return '{}\n{}'.format(line_original, line_cuneiform)


def cuneify_file(cache, file_name, show_transliteration):
    ''' Given a text file with one or more lines of transliterated text, print out the corresponding
        version in cuneiform
    '''
    output = ''
    with open(file_name) as input_file:
        for line in input_file:
            output += cuneify_line(cache, line, show_transliteration)
            output += '\n'
            # If also showing transliteration then an extra blank line aids legibility
            if show_transliteration:
                output += '\n'
    return output


def ordered_symbol_to_transliterations(cache, transliteration, return_unrecognised=False):
    ''' Given a transliteration, which might be a multi-line input, grab all tokens and build up a symbol list. 
        This will be an OrderedDict mapping symbol to transliteration tokens, in the order of appearance

        If return_unrecognised is set to True, additionally return a list of symbols that aren't recognised.
    '''
    result = OrderedDict()
    unrecognised = []

    # Concatenate symbols over multiple lines of transliteration
    tokens = sum((list(re.split(TOKEN_REGEX, transliteration_line.strip())) for transliteration_line in transliteration.split()), 
                 [])
    for token in tokens:
        try:
            cuneiform_symbol = cache.get_cuneiform(token)
        except (UnrecognisedSymbol, TransliterationNotUnderstood):
            if return_unrecognised and token not in unrecognised:
                unrecognised.append(token)
                continue
            else:
                raise
        if cuneiform_symbol not in result:
            result[cuneiform_symbol] = []

        # Only show each token once!
        if token not in result[cuneiform_symbol]:
            result[cuneiform_symbol].append(token)

    # Return the appropriate things
    if return_unrecognised:
        return result, unrecognised
    else:
        return result


def main():
    parser = ArgumentParser()
    parser.add_argument('input_file', help='Text file with transliterated cuneiform')
    parser.add_argument('--show-transliteration', action='store_true',
                        help='By default just show cuneiform. If this is set, '
                             'also display original transliteration')
    parser.add_argument('--cache', help='Use specified cache file',
                        default='cuneiform_cache.pickle')
    args = parser.parse_args()
    with FileCuneiformCache(cache_file_path=args.cache) as cache:
        print(cuneify_file(cache, args.input_file, args.show_transliteration))


if __name__ == '__main__':
    main()

