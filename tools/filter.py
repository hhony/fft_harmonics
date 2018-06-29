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
        self.third = [-1, -1]
        self.dominant = [-1 , -1, -1]


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
        # center filter on A1 to C8 within A4 to A5 window
        self._upper_window_limit = 830.61 + ((880.0 - 830.61) / 2) # halfway between A♯|B♭ below octave
        self._lower_window_limit = 440.0 - ((440.0 - 415.305) / 2) # halfway between A♯|B♭ below unison
        self._upper_filter_limit = 523.25 * 4      # upper C on piano keyboard (C8)
        self._lower_filter_limit = 440.0 / (2 * 3) # lower A on piano keyboard (A1)
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
        self._minor_3rd = 3
        self._major_3rd = 4
        self._dominant_4th = 5
        self._dominant_5th = 6
        self._note_set = list()
        self._note_labels = list()
        self._maxmag_freq = None
        # audio weights       [   -3,    -2,    -1,     0,      1,     2,      3,     4]
        self._profile_gains = [0.075, 0.150, 0.666,  0.850, 0.666, 0.666,  0.333, 0.150]
        self._profile_notes = [0 for _ in range(-3, 5)]
        self._root = ''
        self._third = [-1, -1]
        self._dominant = [-1, -1, -1]

    def threshold(self) -> ndarray:
        return self._threshold

    def change_root(self, root: str, test=False) -> int:
        if root and root != self._root:
            if not test:
                logger.debug('change root: (%s) from (%s)', root, self._root)
                self._root = root
            else:
                logger.debug('test root: %s from %s', root, self._root)
                return self._roots.index(root)
        return self._roots.index(self._root)

    def test_root(self, index: int) -> int:
        if index > 0:
            return self.change_root(self._roots[index], True)
        return index

    def get_interval(self, index: int, offset: int):
        return (index + offset) % len(self._roots)

    def build_profile(self, nl: NoteLabel):
        if nl.octave >= -3 and nl.octave <= 4:
            _idx = nl.octave + 3
            self._profile_notes[_idx] += nl.magnitude
        else:
            logger.warning('out of range: %s at (%0.3f, %.3g)', nl.label, nl.frequency, nl.magnitude)

    def build_histogram(self, histogram: list, index: int, octave: int):
        if octave >= -3 and octave <= 4:
            _idx = octave + 3
            if index in self._note_set:
                if histogram[index] < 0:
                    histogram[index] = self._profile_notes[_idx]
                    return
                histogram[index] += self._profile_notes[_idx]
        else:
            logger.warning('skipping: %s in octave: %s', self._roots[index], octave)

    def parse_histogram(self, histogram: list, label='') -> int:
        if self._verbose:
            logger.debug('parse (%s) histogram: %s', label, ['%.3g' % bar for bar in histogram])
        return histogram.index(max(histogram))

    def find_note(self, value: float, magnitude=0.) -> (NoteLabel or None):
        if value >= self._lower_filter_limit and value <= self._upper_filter_limit:
            if self._verbose:
                logger.debug('finding: %.3f with mag: %.3g', value, magnitude)
            note = NoteLabel()
            note.frequency = value
            note.magnitude = magnitude
            # find octave shift
            _upper = self._upper_window_limit
            _lower = self._lower_window_limit
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
                        self.get_interval(_index, self._minor_3rd),
                        self.get_interval(_index, self._major_3rd)
                    ]
                elif interval in [4, 5] and interval < 5:
                    note.dominant[0] = self.get_interval(_index, self._dominant_4th)
                    note.dominant[2] = self.get_interval(_index, self._dominant_5th)
            if self._verbose:
                logger.debug('found: %s is "%s", shifted: %s', value, note.label, note.octave)
            return note
        if self._verbose:
            logger.debug('outside filter range: (%s, %s)', value, magnitude)
        return None

    def find_maxima(self) -> bool:
        for i, idx in zip(self._y, range(len(self._y))):
            if i > self._magnitude:
                self._yy.append(i)
                self._xx.append(self._x[idx])
        if self._yy:
            self._note_labels = [self.find_note(x, y) for x, y in zip(self._xx, self._yy)]
            if None in self._note_labels:
                _temp = self._note_labels.copy()
                self._note_labels.clear()
                for i in range(len(_temp)):
                    if _temp[i] is not None:
                        self._note_labels.append(_temp[i])
            if not self._note_labels:
                return False
            _max_mag = [note.magnitude for note in self._note_labels]
            _max_idx = _max_mag.index(max(_max_mag))
            self._maxmag_freq = self._note_labels[_max_idx]
            self.change_root(self._maxmag_freq.label) # first pass guess
            self._note_set = [self._roots.index(note.label) for note in self._note_labels]
            logger.debug('max: (%s) _n: %s', self._maxmag_freq.label, self._note_set)
            if self._verbose:
                logger.debug('labels _n: %s', [self._roots[i] for i in self._note_set])
            logger.debug('_xx: %s', [str('%.3f' % note.frequency) for note in self._note_labels])
            logger.debug('_yy: %s', [str('%.3g' % note.magnitude) for note in self._note_labels])
            return True
        return False

    def find_spacial_profile(self):
        for nl in self._note_labels:
            self.build_profile(nl)
        for i in range(len(self._profile_notes)):
            self._profile_notes[i] *=  self._profile_gains[i]
        if self._verbose:
            logger.debug('spacial profile: %s', self._profile_notes)

    def find_intervals(self):
        for interval in range(2, 8):
            _histogram_major = [-1 for _ in range(len(self._roots))]
            _histogram_minor = [-1 for _ in range(len(self._roots))]
            for nl in self._note_labels:
                if interval is 3:
                    self.build_histogram(_histogram_minor, nl.third[0], nl.octave)
                    self.build_histogram(_histogram_major, nl.third[1], nl.octave)
                elif interval in [4, 5] and interval < 5:
                    self.build_histogram(_histogram_minor, nl.dominant[0], nl.octave)
                    self.build_histogram(_histogram_major, nl.dominant[2], nl.octave)
            if interval is 3:
                self._third[0] = self.test_root(self.parse_histogram(_histogram_minor, 'minor 3rd'))
                self._third[1] = self.test_root(self.parse_histogram(_histogram_major, 'major 3rd'))
            elif interval in [4, 5] and interval < 5:
                self._dominant[0] = self.test_root(self.parse_histogram(_histogram_minor, '4th'))
                self._dominant[2] = self.test_root(self.parse_histogram(_histogram_major, '5th'))

    def find_relative_dominant(self):
        if self._dominant[2] > -1:
            self.change_root(self._roots[self._dominant[2]])

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
            self.find_spacial_profile()
            self.find_intervals()
            self.find_relative_dominant()
            _third = self.find_3rds()
        return { 'root': self._root, 'third': _third }
