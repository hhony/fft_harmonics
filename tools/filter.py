from numpy import empty, greater, ndarray
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
        self.third = [-1, -1]


class TriadFilter:
    def __init__(self, x, y, verbose=False, threshold=5000.):
        self._verbose = verbose
        self._magnitude = threshold
        self._threshold = empty(y.size)
        self._threshold.fill(self._magnitude)
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
        self._min_3rd = [
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
        self._maj_3rd = [
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
        self._root = ''
        self._third = [-1, -1]
        self._dominate = [-1, -1, -1]

    def threshold(self) -> ndarray:
        return self._threshold

    def change_root(self, root: str, test=False) -> int:
        if root and root != self._root:
            logger.debug('change root: (%s) from (%s)', root, self._root)
            if not test:
                self._root = root
            else:
                return self._roots.index(root)
        return self._roots.index(self._root)

    def test_root(self, index: int) -> int:
        if index > 0:
            return self.change_root(self._roots[index], True)
        return index

    def build_histogram(self, histogram: list, index: int):
        if histogram[index] < 0:
            histogram[index] = 1
            return
        histogram[index] += 1

    def parse_histogram(self, histogram: list) -> int:
        if self._verbose:
            logger.debug('parse histogram: %s', histogram)
        return histogram.index(max(histogram))

    def find_note(self, value: float, magnitude=0.) -> NoteLabel:
        if self._verbose:
            logger.debug('finding: %s with mag: %s', value, magnitude)
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
        for interval in range(2, 8):
            if interval == 3:
                note.third = [
                    self._min_3rd.index(note.label),
                    self._maj_3rd.index(note.label)
                ]
            elif interval in [4, 5] and interval < 5:
                note.fifth = self._fifths.index(note.label)
        if self._verbose:
            logger.debug('found: %s is "%s", shifted: %s', value, note.label, note.octave)
        return note

    def find_maxima(self) -> bool:
        for i, idx in zip(self._y, range(len(self._y))):
            if i > self._magnitude:
                self._yy.append(i)
                self._xx.append(self._x[idx])
        if self._yy:
            _max_idx = self._yy.index(max(self._yy))
            self._maxmag_freq = self.find_note(self._xx[_max_idx], self._yy[_max_idx])
            self.change_root(self._maxmag_freq.label) # first pass guess
            self._note_labels = [self.find_note(x, y) for x, y in zip(self._xx, self._yy)]
            self._note_set = [self._roots.index(note.label) for note in self._note_labels]
            logger.debug('max: (%s) _n: %s', self._maxmag_freq.label, self._note_set)
            logger.debug('_xx: %s', [note.frequency for note in self._note_labels])
            logger.debug('_yy: %s', [note.magnitude for note in self._note_labels])
            return True
        return False

    def find_major_minor(self, interval: int):
        _histogram_major = [-1 for i in range(12)]
        _histogram_minor = [-1 for i in range(12)]
        for nl in self._note_labels:
            if interval is 3:
                if nl.third[0] in self._note_set:
                    self.build_histogram(_histogram_minor, nl.third[0])
                if nl.third[1] in self._note_set:
                    self.build_histogram(_histogram_major, nl.third[1])
            elif interval in [4, 5] and interval < 5:
                if nl.fifth in self._note_set:
                    self.build_histogram(_histogram_major, nl.fifth)
        if interval is 3:
            self._third[0] = self.test_root(self.parse_histogram(_histogram_minor))
            self._third[1] = self.test_root(self.parse_histogram(_histogram_major))
        elif interval in [4, 5] and interval < 5:
            self._dominate[2] = self.test_root(self.parse_histogram(_histogram_major))

    def find_intervals(self):
        for interval in range(2, 8):
            self.find_major_minor(interval)

    def find_relative_dominate(self):
        _idx = self.parse_histogram(self._dominate)

        if _idx == 2 and self._dominate[2] > -1:
            self.change_root(self._roots[self._dominate[2]])

    def find_3rds(self) -> str:
        _output = [' maj', ' m']
        _stores = -1
        if self._third[1] and self._third[0]: # major and minor
            if self._third[1] in self._note_set and self._third[0] not in self._note_set:
                _stores = 0
            elif self._third[0] in self._note_set and self._third[1] not in self._note_set:
                _stores = 1
        else: # major or minor
            if self._third[1] in self._note_set:
                _stores = 1
            elif self._third[0] in self._note_set:
                _stores = 0
        if _stores > -1:
            self.change_root(self._roots[self._third[_stores]])
            return _output[_stores]
        return ''

    def filter(self) -> dict:
        _third = ''
        if self.find_maxima():
            self.find_intervals()
            self.find_relative_dominate()
            _third = self.find_3rds()
        return { 'root': self._root, 'third': _third }
