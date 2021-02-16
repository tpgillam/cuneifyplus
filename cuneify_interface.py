# -*- coding: utf8 -*-

import itertools
import os
import pickle
import re

from abc import ABCMeta, abstractmethod
from argparse import ArgumentParser
from collections import OrderedDict


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
TOKEN_REGEX = r'-| |\.'


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

                   # Replace em-dash and en-dash with normal dash
                   '–': '-',
                   '—': '-',
                   }
ACUTE_VOWELS = {'á': 'a', 'é': 'e', 'í': 'i', 'ú': 'u'}
GRAVE_VOWELS = {'à': 'a', 'è': 'e', 'ì': 'i', 'ù': 'u'}

# Extend the dictionaries at import time to include uppercase versions
REPLACEMENT_MAP.update({key.upper(): value.upper() for key, value in REPLACEMENT_MAP.items()})
ACUTE_VOWELS.update({key.upper(): value.upper() for key, value in ACUTE_VOWELS.items()})
GRAVE_VOWELS.update({key.upper(): value.upper() for key, value in GRAVE_VOWELS.items()})


def contains_ascii(byte_array, ignore_space=True):
    ''' Returns true if any character in the given bytes object is an ascii character. '''
    if not byte_array:
        return False
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


class CuneiformCacheBase:
    ''' Abstract class representing a cuneiform class. It is a context manager, where the cache will be loaded
        on entry and updated at exit.

        The public API is the get_cuneiform() method, which is given one transliteration token.
    '''

    __metaclass__ = ABCMeta

    def __init__(self):
        # These are symbols which, if found within a token, are stripped and
        # placed to the end, whilst the remainder is cunefied as normal. Similar
        # logic applies to those that would be placed at the start
        self._characters_to_strip_and_place_at_start = ('[')
        self._characters_to_strip_and_place_at_end = ('!', '?', ']')

        # Runtime storage for the cache
        self.transliteration_to_cuneiform = {}

        # This variable allows children to decide to not do writing, if they want.
        self._cache_modified = False

    @abstractmethod
    def __enter__(self):
        ''' Get the current transliteration -> cuneiform map from storage '''

    @abstractmethod
    def __exit__(self, type_, value, traceback):
        ''' Update the cache with the current transliteration, cuneiform pairs. It will overwrite the given
            values if present
        '''

    def _get_cuneiform_bytes(self, transliteration):
        ''' Get the cuneiform bytes array corresponding to the given transliteration, using the cache if available. '''
        if transliteration == '':
            # The empty string corresponds to no cuneiform symbol!
            return b''
        if transliteration not in self.transliteration_to_cuneiform:
            raise UnrecognisedSymbol(transliteration)
            # return transliteration.encode('utf8')
        return self.transliteration_to_cuneiform[transliteration]

    def get_stripped_transliteration(self, transliteration):
        ''' Return the basic transliteration symbol, without extra characters like [, !, ? etc. '''
        result = transliteration
        for char in itertools.chain(self._characters_to_strip_and_place_at_start,
                                    self._characters_to_strip_and_place_at_end):
            result = result.replace(char, '')
        return result

    def _should_pass_through(self, transliteration):
        ''' Return True iff no attempt to cuneify this string should be made '''
        # Strings of x or X should be ignored - they represent unreadable symbols
        lower_case_characters = set(transliteration.lower())
        if lower_case_characters == {'x'}:
            return True

        # Special characters that are left as-is
        unmodified_sybols = ('?', '!', '[', ']')
        if transliteration in unmodified_sybols:
            return True

        # Cuneify!
        return False

    def get_cuneiform(self, transliteration, include_extra_chars=True):
        ''' Get the UTF-8 string corresponding to the cuneiform that we want.
            If include_extra_chars is set to False, then characters like [, !, and ? will not be included in the symbols
            returned, though in normal usage they would be included.
        '''
        # First ascertain whether it is a spcecial case, in which case don't do
        # anything
        if self._should_pass_through(transliteration):
            return transliteration

        # Create buffers of characters that should go to the start / end, and
        # strip them from the transliteration
        start = ''
        end = ''
        stripped_transliteration = ''
        for char in transliteration:
            if char in self._characters_to_strip_and_place_at_start:
                start += char
            elif char in self._characters_to_strip_and_place_at_end:
                end += char
            else:
                stripped_transliteration += char

        cuneiform = self._get_cuneiform_bytes(stripped_transliteration).decode('utf-8')
        if not include_extra_chars:
            return cuneiform
        return start + cuneiform + end


class FileCuneiformCache(CuneiformCacheBase):
    ''' Store the cuneiform cache in a pickle file '''

    def __init__(self, cache_file_path, read_only=False):
        super().__init__()
        self._cache_file_path = cache_file_path
        self._read_only = read_only

    def __enter__(self):
        super().__enter__()
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
        if self._cache_modified:
            self._write_cache_file()

    def _load_cache_file(self):
        ''' Worker method to load the cache file into the local variable '''
        with open(self._cache_file_path, 'rb') as cache_file:
            stored_cache = pickle.load(cache_file)
            self.transliteration_to_cuneiform.update(stored_cache)

    def _write_cache_file(self):
        ''' Worker method to write the cache file to disk '''
        if self._read_only:
            # We cannot update the cache file, since we're in read-only mode
            return
        with open(self._cache_file_path, 'wb') as cache_file:
            pickle.dump(self.transliteration_to_cuneiform, cache_file)
        # The cache is no longer modified
        self._cache_modified = False


class MySQLCuneiformCache(CuneiformCacheBase):
    ''' Store the cuneiform cache in a mysql table '''

    def __init__(self, host, user, password, dbname):
        super().__init__()
        self._host = host
        self._user = user
        self._password = password
        self._dbname = dbname

    def __enter__(self):
        super().__enter__()

        import MySQLdb
        self._conection = MySQLdb.connect(host=self._host, user=self._user,
                                          passwd=self._password, db=self._dbname)
        cursor = self._connection.cursor()

        cursor.execute('select * from lookup')
        rows = cur.fetchall()

        if len(rows) == 0:
            # No data with which to update our cache
            return

        if len(rows) > 1:
            raise RuntimeError("Expected at most 1 row, but got {}".format(len(rows)))

        row = rows[0]
        stored_cache = pickle.loads(row[1])
        self.transliteration_to_cuneiform.update(stored_cache)
        return self

    def __exit__(self, type_, value, traceback):
        if not self._cache_modified:
            return

        new_value = pickle.dumps(self.transliteration_to_cuneiform)

        cursor = self._connection.cursor()
        # Clear existing row, if present
        cursor.execute('DELETE FROM lookup')

        # Insert the new data
        cursor.execute('INSERT INTO lookup (stuff) VALUES (%s)', (new_value,))

        self._connection.close()


def cuneify_line_structured(cache, transliteration):
    ''' Take a line of transliteration and return structured data of
        - tokens, eg `tok1`
        - separators, eg `.`
        - symbols, eg `𒌉`
        - unrecognized tokens, eg `bob`
    '''
    transliteration = transliteration.strip()
    # Split using alphanumeric characters (\w)
    tokens = re.split(TOKEN_REGEX, transliteration)

    separators = re.findall(TOKEN_REGEX, transliteration)
    separators.append('')
    line_original = ''
    line_cuneiform = ''
    symbols = []
    unrecognized_tokens = []
    for token in tokens:
        try:
            symbol = cache.get_cuneiform(token)
        except (UnrecognisedSymbol, TransliterationNotUnderstood):
            symbol = None
            unrecognized_tokens.append(token)
        symbols.append(symbol)

    return (tokens, separators, symbols, unrecognized_tokens)

def cuneify_line(cache, transliteration, show_transliteration, unrecognized_indicator="?"):
    ''' Take a line of transliteration and display the output, nicely formatted, on the terminal.
        Should be used whilst in the context of cache.
        unrecognized_indicator : String to display if token not recognized. If empty string,
          the token will be returned as-is.
    '''

    (tokens, separators, raw_symbols, unrecognized_tokens) = cuneify_line_structured(cache, transliteration)

    # Substitube chosen string for unrecognized tokens
    symbols = [s if s is not None else t if unrecognized_indicator=="" else unrecognized_indicator for (t, s) in zip(tokens, raw_symbols)]

    if show_transliteration:
        line_original = ""
        line_cuneiform = ""
        for token, separator, symbol in zip(tokens, separators, symbols):
            if symbol is None:
                symbol = token if unrecognized_indicator=="" else unrecognized_indicator
            width = max(len(token + separator), len(symbol))
            line_original += (token + separator).ljust(width)
            line_cuneiform += symbol.ljust(width)
        return '{}\n{}'.format(line_original, line_cuneiform)
    else:
        return " ".join(symbols)


def cuneify_iterator(cache, iterator, show_transliteration, parse_atf=True):
    output = ''
    if parse_atf:
        for line in iterator:
            atf_line_parts = re.search('^([0-9]+\.)([ \t]*)(.*)', line)
            if atf_line_parts:
                transliteration = atf_line_parts.group(3)
                output += line
                output += "#" + atf_line_parts.group(2) + cuneify_line(cache, transliteration, show_transliteration) + "\n"
            else:
                output += line
    else:
        for line in iterator:
            output += cuneify_line(cache, line, show_transliteration)
            output += '\n'
            # If also showing transliteration then an extra blank line aids legibility
            if show_transliteration:
                output += '\n'
    return output


def cuneify_file(cache, file_name, show_transliteration, parse_atf=True):
    ''' Given a text file with one or more lines of transliterated text, print out the corresponding
        version in cuneiform
    '''
    with open(file_name) as iterator:
        return cuneify_iterator(cache, iterator, show_transliteration, parse_atf=parse_atf)


def ordered_symbol_to_transliterations(cache, transliteration, return_unrecognised=False):
    ''' Given a transliteration, which might be a multi-line input, grab all tokens and build up a symbol list.
        This will be an OrderedDict mapping symbol to transliteration tokens, in the order of appearance

        If return_unrecognised is set to True, additionally return a set of symbols that aren't recognised.
    '''
    result = OrderedDict()
    unrecognised = set()

    # Concatenate symbols over multiple lines of transliteration
    tokens = sum((list(re.split(TOKEN_REGEX, transliteration_line.strip()))
                 for transliteration_line in transliteration.split()),
                 [])
    for token in tokens:
        # Remove special characters that we don't need for a sign list
        token = cache.get_stripped_transliteration(token)

        try:
            cuneiform_symbol = cache.get_cuneiform(token)
        except (UnrecognisedSymbol, TransliterationNotUnderstood):
            if return_unrecognised:
                unrecognised.add(token)
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
    parser.add_argument('--parse-atf', action='store_true',
                        help='If this is set parse file as .atf formatted')
    parser.add_argument('--symbol-list', action='store_true',
        help='If this is set, show a mapping between the transliterated symbols and cuneiform.')
    parser.add_argument('--cache', help='Use specified cache file',
                        default='cuneiform_cache.pickle')
    args = parser.parse_args()
    with FileCuneiformCache(cache_file_path=args.cache) as cache:
        if args.symbol_list:
            with open(args.input_file) as input_file:
                symbol_to_transliterations, unrecognised_tokens = ordered_symbol_to_transliterations(
                    cache,
                    input_file.read(),
                    return_unrecognised=True)
                print('Symbol map:')
                for symbol, transliterations in symbol_to_transliterations.items():
                    print(' {} :  {}'.format(symbol, transliterations))
                print()
                print('Unrecognised symbols:')
                print(unrecognised_tokens)
        else:
            print(cuneify_file(cache, args.input_file, args.show_transliteration, args.parse_atf))


if __name__ == '__main__':
    main()
