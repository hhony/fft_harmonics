from numpy import greater
from scipy.signal import argrelextrema

from .log import logger


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
        self._note_labels = []
        self._maxmag_freq = ''
        self._root = ''
        self._third = ''

    def find_note(self, value: float):
        if value > self._freqs[len(self._freqs)-1]:
            _value = [float(value % i) for i in self._freqs]
        elif value < self._freqs[0]:
            _value = [float(i % value) for i in self._freqs]
        else:
            _value = [abs(float(1 - (value/i))) for i in self._freqs]
        _index = str(self._freqs[_value.index(min(_value))])
        # _index_abs = str(_freqs[_value_abs.index(min(_value_abs))])
        # if (_index_abs != _index_mod):
        #     return '%s vs. %s' % (_notes[_index_mod], _notes[_index_abs])
        return self._notes[_index]

    def find_maxima(self):
        for i, idx in zip(self._y, range(len(self._y))):
            if i > self._magnitude:
                self._yy.append(i)
                self._xx.append(self._x[idx])
        if self._yy:
            self._maxmag_freq = self.find_note(self._xx[self._yy.index(max(self._yy))])
            self._note_labels = [self.find_note(i) for i in self._xx]
            # logger.debug('_yy: %s, _xx: %s', self._yy, self._xx)
            logger.debug('max: (%s) _n: %s', self._maxmag_freq, self._note_labels)
        else:
            logger.info('...')

    def find_circle_of_fifth(self):
        for i in self._note_labels:
            _root = self._fifths[i]
            if _root in self._note_labels and _root != self._maxmag_freq:
                self._root = _root
                break

    def find_major_minor(self):
        for i in self._note_labels:
            _root = self._minors[i]
            if _root in self._note_labels:
                self._third = 'm'
                break
            _root = self._majors[i]
            if _root in self._note_labels:
                self._third = 'maj'
                break

    def filter(self) -> dict:
        self.find_maxima()
        self.find_circle_of_fifth()
        self.find_major_minor()
        return { 'root': self._root, 'third': self._third }