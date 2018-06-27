from numpy import greater
from scipy.signal import argrelextrema

from .log import logger

class NoteLabel:
    def __init__(self, frequency=0., magnitude=0.):
        self.frequency = frequency
        self.magnitude = magnitude
        self.octave = 0
        self.index = 0
        self.label = ''
        self.fifth = ''
        self.third = dict()


class TriadFilter:
    def __init__(self, x, y):
        self._magnitude = 5000
        self._maxima = argrelextrema(y, greater)
        for i in self._maxima:
            self._y = y[i]
            self._x = x[i]
        self._yy = []
        self._xx = []
        self._upper_limit = 830.61 + ((880.0 - 830.61) / 2) # halfway between A♯|B♭ below octave
        self._lower_limit = 440.0 - ((440.0 - 415.305) / 2) # halfway between A♯|B♭ below unison
        self._freqs = [
            440.0,
            466.16,
            493.88,
            523.25,
            554.37,
            587.33,
            622.25,
            659.26,
            698.46,
            739.99,
            783.99,
            830.61
        ]
        self._roots = [
            'A',
            'A♯|B♭',
            'B',
            'C',
            'C♯|D♭',
            'D',
            'D♯|E♭',
            'E',
            'F',
            'F♯|G♭',
            'G',
            'G♯|A♭'
        ]

        self._fifths = [
            'E',
            'F',
            'F♯|G♭',
            'G',
            'G♯|A♭',
            'A',
            'A♯|B♭',
            'B',
            'C',
            'C♯|D♭',
            'D',
            'D♯|E♭'
        ]
        self._minors = [
            'C',
            'C♯|D♭',
            'D',
            'D♯|E♭',
            'E',
            'F',
            'F♯|G♭',
            'G',
            'G♯|A♭',
            'A',
            'A♯|B♭',
            'B'
        ]
        self._majors = [
            'C♯|D♭',
            'D',
            'D♯|E♭',
            'E',
            'F',
            'F♯|G♭',
            'G',
            'G♯|A♭',
            'A',
            'A♯|B♭',
            'B',
            'C'
        ]
        self._note_set = list()
        self._note_labels = list()
        self._maxmag_freq = None
        self._has_fifth = False
        self._root = ''
        self._third = ''

    def find_note(self, value: float, magnitude=0.) -> NoteLabel:
        # logger.debug('finding: %s with mag: %s', value, magnitude)
        note = NoteLabel()
        note.frequency = value
        note.magnitude = magnitude
        # find octave shift
        _upper = self._upper_limit
        _lower = self._lower_limit
        _octave = 0
        _harmonic = value
        if _harmonic > _upper:
            while _harmonic > _upper:
                _harmonic /= 2
                _octave += 1
        elif _harmonic < _lower:
            while _harmonic < _lower:
                _harmonic *= 2
                _octave += 1
            _octave *= -1
        # apply shifted
        if _octave < 0:
            _freqs = [float(_f/(-2 * _octave)) for _f in self._freqs]
        elif _octave > 0:
            _freqs = [float(_f * (2 * _octave)) for _f in self._freqs]
        else:
            _freqs = self._freqs
        note.octave = _octave
        # find nearest
        _value = [abs(float(value - i)) for i in _freqs]
        _index = _value.index(min(_value))
        note.index = _index
        note.label = self._roots[note.index]
        note.fifth = self._roots[self._fifths.index(note.label)]
        note.third = {
            'minor': self._roots[self._minors.index(note.label)],
            'major': self._roots[self._majors.index(note.label)]
        }
        # logger.debug('found: %s is "%s", shifted: %s', value, note.label, note.octave)
        return note

    def find_maxima(self):
        for i, idx in zip(self._y, range(len(self._y))):
            if i > self._magnitude:
                self._yy.append(i)
                self._xx.append(self._x[idx])
        if self._yy:
            _max_idx = self._yy.index(max(self._yy))
            self._maxmag_freq = self.find_note(self._xx[_max_idx], self._yy[_max_idx])
            self.change_root(self._maxmag_freq.label) # first pass guess
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

    def change_root(self, root: str) -> bool:
        if root and root != self._root:
            logger.debug('change root: (%s) from (%s)', root, self._root)
            self._root = root
            return True
        return False

    def find_relative_dominate(self):
        _histogram = dict()
        for nl in self._note_labels:
            _fifth = nl.fifth
            if _fifth in self._note_set:
                self.build_histogram(_histogram, _fifth)
        _root = self.parse_historgram(_histogram)
        self._has_fifth = self.change_root(_root)

    def find_major_minor(self):
        _histogram_major = dict()
        _histogram_minor = dict()
        for nl in self._note_labels:
            if nl.third['minor'] in self._note_set:
                self.build_histogram(_histogram_minor, nl.third['minor'])
            if nl.third['major'] in self._note_set:
                self.build_histogram(_histogram_major, nl.third['major'])
        _root_minor = self.parse_historgram(_histogram_minor)
        _root_major = self.parse_historgram(_histogram_major)
        if _root_major and _root_minor:
            if _root_major in self._note_set and _root_minor not in self._note_set:
                self._third = ' maj'
                self.change_root(_root_major)
            elif _root_minor in self._note_set and _root_major not in self._note_set:
                self._third = ' m'
                self.change_root(_root_minor)
            else:
                _major_value = _histogram_major[_root_major]
                _minor_value = _histogram_minor[_root_minor]
                if _major_value > _minor_value:
                    self._third = ' maj'
                    self.change_root(_root_major)
                elif _minor_value > _major_value:
                    self._third = ' m'
                    self.change_root(_root_minor)
        else: # _root_major or _root_minor
            if _root_major in self._note_set:
                self._third = ' maj'
                self.change_root(_root_major)
            elif _root_minor in self._note_set:
                self._third = ' m'
                self.change_root(_root_minor)

    def filter(self) -> dict:
        self.find_maxima()
        self.find_relative_dominate()
        self.find_major_minor()
        return { 'root': self._root, 'third': self._third }