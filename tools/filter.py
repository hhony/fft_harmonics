from numpy import greater
from scipy.signal import argrelextrema

from .log import logger

class NoteLabel:
    def __init__(self, frequency=0., magnitude=0.):
        self.frequency = frequency
        self.magnitude = magnitude
        self.octave = 0
        self.label = ''
        self.fifth = ''
        self.third = dict()


class TriadFilter:
    def __init__(self, x, y):
        self._magnitude = 8000
        self._maxima = argrelextrema(y, greater)
        for i in self._maxima:
            self._y = y[i]
            self._x = x[i]
        self._yy = []
        self._xx = []
        self._freqs = [440.0, 466.16, 493.88, 523.25, 554.37, 587.33, 622.25, 659.26, 698.46, 739.99, 783.99, 830.61]
        self._notes = {
            '440.0' : 'A',
            '466.16': 'A♯|B♭ ',
            '493.88': 'B',
            '523.25': 'C',
            '554.37': 'C♯|D♭ ',
            '587.33': 'D',
            '622.25': 'D♯|E♭ ',
            '659.26': 'E',
            '698.46': 'F',
            '739.99': 'F♯|G♭ ',
            '783.99': 'G',
            '830.61': 'G♯|A♭ '
        }
        self._fifths = {
            'E'      : 'A',
            'F'      : 'A♯|B♭ ',
            'F♯|G♭ ' : 'B',
            'G'      : 'C',
            'G♯|A♭ ' : 'C♯|D♭ ',
            'A'      : 'D',
            'A♯|B♭ ' : 'D♯|E♭ ',
            'B'      : 'E',
            'C'      : 'F',
            'C♯|D♭ ' : 'F♯|G♭ ',
            'D'      : 'G',
            'D♯|E♭ ' : 'G♯|A♭ '
        }
        self._minors = {
            'C'      : 'A',
            'C♯|D♭ ' : 'A♯|B♭ ',
            'D'      : 'B',
            'D♯|E♭ ' : 'C',
            'E'      : 'C♯|D♭ ',
            'F'      : 'D',
            'F♯|G♭ ' : 'D♯|E♭ ',
            'G'      : 'E',
            'G♯|A♭ ' : 'F',
            'A'      : 'F♯|G♭ ',
            'A♯|B♭ ' : 'G',
            'B'      : 'G♯|A♭ '
        }
        self._majors = {
            'C♯|D♭ ' : 'A',
            'D'      : 'A♯|B♭ ',
            'D♯|E♭ ' : 'B',
            'E'      : 'C',
            'F'      : 'C♯|D♭ ',
            'F♯|G♭ ' : 'D',
            'G'      : 'D♯|E♭ ',
            'G♯|A♭ ' : 'E',
            'A'      : 'F',
            'A♯|B♭ ' : 'F♯|G♭ ',
            'B'      : 'G',
            'C'      : 'G♯|A♭ '
        }
        self._note_set = list()
        self._note_labels = list()
        self._maxmag_freq = None
        self._has_fifth = False
        self._root = ''
        self._third = ''

    def find_note(self, value: float, magnitude=0.) -> NoteLabel:
        note = NoteLabel()
        note.frequency = value
        note.magnitude = magnitude
        _upper = self._freqs[len(self._freqs)-1]
        _lower = self._freqs[0]
        _octave = 0
        if value > _upper:
            while value > _upper:
                value /= 2
                _octave += 1
        elif value < _lower:
            while value < _lower:
                value *= 2
                _octave += 1
            _octave *= -1
        _value = [abs(float(1 - (value/i))) for i in self._freqs]
        _index = str(self._freqs[_value.index(min(_value))])
        note.label = self._notes[_index]
        note.fifth = self._fifths[note.label]
        note.third = { 'minor': self._minors[note.label], 'major': self._majors[note.label] }
        return note

    def find_maxima(self):
        for i, idx in zip(self._y, range(len(self._y))):
            if i > self._magnitude:
                self._yy.append(i)
                self._xx.append(self._x[idx])
        if self._yy:
            _max_idx = self._yy.index(max(self._yy))
            self._maxmag_freq = self.find_note(self._xx[_max_idx], self._yy[_max_idx])
            self._note_labels = [self.find_note(x, y) for x, y in zip(self._xx, self._yy)]
            self._note_set = [note.label for note in self._note_labels]
            logger.debug('max: (%s) _n: %s', self._maxmag_freq.label, self._note_set)
            logger.debug('_xx: %s', [note.frequency for note in self._note_labels])
            logger.debug('_yy: %s', [note.magnitude for note in self._note_labels])
        # else:
        #     logger.debug('...')

    def build_histogram(self, histogram: dict, key: str):
        if key not in histogram:
            histogram[key] = 1
            return
        histogram[key] += 1

    def parse_historgram(self, histogram: dict) -> str:
        _max = 0
        _root = ''
        for key in histogram:
            _value = histogram[key]
            if _value > _max:
                _max = _value
                _root = key
        return _root

    def find_relative_dominate(self):
        _histogram = dict()
        for nl in self._note_labels:
            _fifth = nl.fifth
            if _fifth in self._note_set:
                self.build_histogram(_histogram, _fifth)
        _root = self.parse_historgram(_histogram)
        if _root and _root != self._maxmag_freq:
            logger.debug('%s vs %s', _root, self._maxmag_freq.label)
            self._has_fifth = True
            self._root = _root

    def find_major_minor(self):
        _histogram_major = dict()
        _histogram_minor = dict()
        for nl in self._note_labels:
            _third = nl.third
            if nl.third['minor'] in self._note_set:
                self.build_histogram(_histogram_minor, _third['minor'])
            if nl.third['major'] in self._note_set:
                self.build_histogram(_histogram_major, _third['major'])
        _root_minor = self.parse_historgram(_histogram_minor)
        _root_major = self.parse_historgram(_histogram_major)
        if (_root_minor and _root_minor == self._root) or (_root_major and _root_major == self._root):
            if _root_major and _root_minor:
                if _root_major in self._note_set and _root_minor not in self._note_set:
                    self._third = ' maj'
                elif _root_minor in self._note_set and _root_major not in self._note_set:
                    self._third = ' m'
                else:
                    _major_value = _histogram_major[_root_major]
                    _minor_value = _histogram_minor[_root_minor]
                    if _major_value > _minor_value:
                        self._third = ' maj'
                    elif _minor_value > _major_value:
                        self._third = ' m'
        elif _root_major:
            if _root_major in self._note_set:
                self._third = ' maj'
            elif _root_minor in self._note_set:
                self._third = ' m'
        # if self._third :
        #     logger.debug('%s, has_fifth: %s', self._root, self._has_fifth)
        #     if self._has_fifth:
        #         self._root = _root

    def filter(self) -> dict:
        self.find_maxima()
        self.find_relative_dominate()
        self.find_major_minor()
        return { 'root': self._root, 'third': self._third }