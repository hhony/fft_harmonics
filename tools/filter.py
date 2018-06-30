from numpy import arange, empty, greater, ndarray, sin, pi
from scipy.signal import argrelextrema
from .log import logger


class NoteLabel:
    def __init__(self, frequency=0., magnitude=0.):
        self.frequency = frequency
        self.magnitude = magnitude
        self.octave = 0
        self.error = 0.
        self.input = 0.
        self.index = 0
        self.label = ''
        self.third = [-1, -1]
        self.dominant = [-1 , -1, -1]


class TriadFilter:
    def __init__(self, x, y, verbose=False, threshold=2e+4):
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
        self._octave_lower = -4
        self._octave_upper = 3
        self._upper_window_limit = 830.61 + (0.5 * (880.0 - 830.61)) # halfway between A♯|B♭ below octave
        self._lower_window_limit = 440.0 - (0.5 * (440.0 - 415.305)) # halfway between A♯|B♭ below unison
        self._upper_filter_limit = 2 * 523.25 * (self._octave_upper - 1)   # upper C on piano keyboard (C8)
        self._lower_filter_limit = 0.5 * 440.0 / (-1 * self._octave_lower) # lower A on piano keyboard (A1)
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
        self._major_2nd = 2
        self._minor_3rd = 3
        self._major_3rd = 4
        self._dominant_4th = 5
        self._dominant_dim = 6
        self._dominant_5th = 7
        # note tracking
        self._note_set = list()
        self._note_mode = [0 for _ in self._roots]
        self._note_labels = list()
        self._minmax_freq = None
        self._step = x[1]
        self._w1 = float(2 * self._freqs[len(self._freqs)-1] * self._octave_upper)
        self._i1 = int(self._w1 / self._step)
        self._profile_ticks = arange(0, x[len(x)-1] + self._step, self._step)
        self._profile_g_win = self._threshold * sin(pi * self._profile_ticks / self._w1)
        # audio weights       [   -4,    -3,    -2,    -1,      0,     1,      2,     3]
        self._profile_gains = [1.000, 1.000, 1.000,  1.000, 1.000, 1.000,  1.000, 1.000]
        self._profile_distr = [0. for _ in range(len(self._profile_gains))]
        # interval tracking
        self._third = [-1, -1]
        self._dominant = [-1, -1, -1]
        # predictions
        self._3rd_bias = [-1, -1]
        self._min_3rd_candidate = -1
        self._maj_3rd_candidate = -1
        self._dom_4th_candidate = -1
        self._dom_dim_candidate = -1
        self._dom_5th_candidate = -1
        self._index = -1
        self._tonic = ''
        self._tense = ''

    def threshold(self) -> ndarray:
        return self._threshold

    def change_root(self, root: int, test=False) -> int:
        if root > -1:
            if not test:
                logger.debug('change root: (%s) from (%s)', self._roots[root], self._tonic)
                self._index = root
                self._tonic = self._roots[self._index]
            else:
                logger.debug('test root: %s from %s', self._roots[root], self._tonic)
                return self._roots.index(self._roots[root])
        return self._index

    def test_root(self, index: int) -> int:
        if index > 0:
            return self.change_root(index, True)
        return index

    def get_interval(self, index: int, offset: int):
        return (index + offset) % len(self._roots)

    def get_profile(self) -> tuple:
        return self._profile_ticks, self._profile_g_win

    def get_mode(self) -> int:
        return self._note_mode.index(max(self._note_mode))

    def build_profile(self, nl: NoteLabel):
        if nl.octave >= self._octave_lower and nl.octave <= self._octave_upper:
            _idx = nl.octave + (-1 * self._octave_lower)
            _mag = self._profile_gains[nl.octave] * nl.magnitude
            _win = int(nl.frequency / self._step)
            nl.input = float(self._profile_g_win[_win] / (nl.magnitude * nl.error))
            self._profile_distr[_idx] += nl.input
            if self._verbose:
                logger.debug('%.3f: %.3g to %.3f, err: %.3f, est: %f' % (
                    nl.frequency, _mag, self._profile_g_win[_win],
                    nl.error, nl.input ))
        else:
            logger.warning('out of range: %s at (%0.3f, %.3g)', nl.label, nl.frequency, nl.magnitude)

    def build_histogram(self, histogram: list, index: int, nl: NoteLabel):
        _octave = nl.octave
        if _octave >= self._octave_lower and _octave <= self._octave_upper:
            _idx = _octave + (-1 * self._octave_lower)
            if index in self._note_set:
                _distr = nl.input + self._profile_distr[_idx]
                if histogram[index] < 0:
                    histogram[index] = _distr
                    return
                histogram[index] += _distr
        else:
            logger.warning('skipping: %s in octave: %s', self._roots[index], _octave)

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
            note.error = _value[_index]
            note.label = self._roots[note.index]
            for interval in range(2, 8):
                if interval is 3:
                    note.third = [
                        self.get_interval(_index, self._minor_3rd),
                        self.get_interval(_index, self._major_3rd)
                    ]
                elif interval in [4, 5] and interval < 5:
                    note.dominant[0] = self.get_interval(_index, self._dominant_4th)
                    note.dominant[1] = self.get_interval(_index, self._dominant_dim)
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
            _max_lbl = self._note_labels[_max_idx].index
            _min_err = [note.error for note in self._note_labels]
            _min_idx = _min_err.index(min(_min_err))
            _min_lbl = self._note_labels[_min_idx].index
            if abs(_max_lbl - _min_lbl) in [self._minor_3rd, self._major_3rd]:
                if _max_lbl > _min_lbl:
                    self._minmax_freq = self._note_labels[_min_idx]
                    self._3rd_bias = [_min_lbl, _max_lbl]
                else:
                    self._minmax_freq = self._note_labels[_max_idx]
                    self._3rd_bias = [_max_lbl, _min_lbl]
            else: # first pass guess
                self._minmax_freq = self._note_labels[_max_idx]
            self.change_root(self._minmax_freq.index)
            self._note_set = [self._roots.index(note.label) for note in self._note_labels]
            for i in self._note_set:
                self._note_mode[i] += 1
            logger.debug('max: (%s) _n: %s', self._minmax_freq.label, self._note_set)
            if self._verbose:
                logger.debug('labels _n: %s', [self._roots[i] for i in self._note_set])
                logger.debug('_xx: %s', [str('%.3f' % note.frequency) for note in self._note_labels])
                logger.debug('_yy: %s', [str('%.3g' % note.magnitude) for note in self._note_labels])
                logger.debug('err: %s', [str('%.3f' % err) for err in _min_err])
            logger.debug('err: min: %s (%d) %s: %.3f',
                         _min_err[_min_idx],
                         _min_idx,
                         self._note_labels[_min_idx].label,
                         self._note_labels[_min_idx].frequency
            )
            logger.debug('mag: max: %s (%d) %s: %.3f',
                         _max_mag[_max_idx],
                         _max_idx,
                         self._note_labels[_max_idx].label,
                         self._note_labels[_max_idx].frequency
            )
            return True
        return False

    def find_spacial_profile(self):
        for nl in self._note_labels:
            self.build_profile(nl)
        logger.debug('|--| spacial profile distribution: %s', [str('%.3f' % i) for i in self._profile_distr])

    def find_intervals(self):
        for interval in range(2, 8):
            _histogram_major = [-1 for _ in range(len(self._roots))]
            _histogram_minor = [-1 for _ in range(len(self._roots))]
            _histogram_dimin = [-1 for _ in range(len(self._roots))]
            for nl in self._note_labels:
                if interval is 3:
                    self.build_histogram(_histogram_minor, nl.third[0], nl)
                    self.build_histogram(_histogram_major, nl.third[1], nl)
                elif interval in [4, 5] and interval < 5:
                    self.build_histogram(_histogram_minor, nl.dominant[0], nl)
                    self.build_histogram(_histogram_dimin, nl.dominant[1], nl)
                    self.build_histogram(_histogram_major, nl.dominant[2], nl)
            if interval is 3:
                self._third[0] = self.test_root(self.parse_histogram(_histogram_minor, 'minor 3rd'))
                self._third[1] = self.test_root(self.parse_histogram(_histogram_major, 'major 3rd'))
                if nl.third[1] > -1 and nl.third[0] > -1:
                    _max_minor = max(_histogram_minor)
                    _max_major = max(_histogram_major)
                    if self.get_interval(nl.third[0], self._dominant_5th) == \
                            self.get_interval(nl.index, self._minor_3rd) or \
                        (_max_minor > _max_major):
                        nl.third[1] = -1
                    elif (_max_major > _max_minor):
                            nl.third[0] = -1
                    else:
                        nl.third[0] = -1
                        nl.third[1] = -1
            elif interval in [4, 5] and interval < 5:
                self._dominant[0] = self.test_root(self.parse_histogram(_histogram_minor, '4th'))
                self._dominant[1] = self.test_root(self.parse_histogram(_histogram_dimin, 'diminished'))
                self._dominant[2] = self.test_root(self.parse_histogram(_histogram_major, '5th'))

    def find_relative_dominant(self):
        for i in range(len(self._dominant)):
            _dom_dim = self._dominant[i]
            if _dom_dim > -1:
                _tense = ''
                if i is 0:
                    self._dom_4th_candidate = _dom_dim
                    _tense += '(4th) '
                elif i is 1:
                    self._dom_dim_candidate = _dom_dim
                    _tense += '(diminished / augmented) '
                elif i is 2:
                    self._dom_5th_candidate = _dom_dim
                    _tense += '(5th) '
                logger.debug("Likely tonic dominant candidate: %s %s", self._roots[_dom_dim], _tense)

    def find_3rds(self):
        _output = [' m', ' maj']
        _stores = -1
        _majmin = ''
        # check bias
        if self._3rd_bias[0] > -1:
            _minor_root = self.get_interval(self._3rd_bias[0], (-1 * self._minor_3rd))
            _major_root = self.get_interval(self._3rd_bias[0], (-1 * self._major_3rd))
            if _minor_root in [self._dom_4th_candidate, self._dom_dim_candidate, self._dominant_5th] \
                    or _minor_root == self.get_mode():
                self._tense = _output[0]
                if self._index != _minor_root:
                    self.change_root(_minor_root)
                return
            elif _major_root in [self._dom_4th_candidate, self._dom_dim_candidate, self._dominant_5th] \
                    or _major_root == self.get_mode():
                self._tense = _output[1]
                if self._index != _major_root:
                    self.change_root(_major_root)
                return
            else:
                self._3rd_bias = [-1, -1]
        # major or minor.. means yes.
        if self._third[1] in self._note_set:
            _stores = 1
            self._min_3rd_candidate = self._third[_stores]
            self._tense = _output[_stores]
            _majmin += '(%s ) ' % (self._tense)
        if self._third[0] in self._note_set:
            _stores = 0
            self._maj_3rd_candidate = self._third[_stores]
            self._tense = _output[_stores]
            _majmin += '(%s ) ' % (self._tense)
        if _stores > -1:
            logger.debug("Likely tonic 3rd candidate: %s %s", self._roots[self._third[_stores]], _majmin)

    def analyze_intervals(self):
        if self._dom_4th_candidate > -1 and self._dom_5th_candidate > -1 and self._3rd_bias[0] == -1:
            _maj_3rd_via_4th = self.get_interval(self._dom_4th_candidate, self._major_3rd)
            _min_3rd_via_4th = self.get_interval(self._dom_4th_candidate, self._minor_3rd)
            # 4th == 5th   and 3rd   == 4th
            # 4th == 5th   and tonic == 3rd
            if (self._index != self._dom_4th_candidate and self._dom_4th_candidate == self._dom_5th_candidate and
                    (self._min_3rd_candidate == _min_3rd_via_4th or self._maj_3rd_candidate == _maj_3rd_via_4th) or
                    (self._min_3rd_candidate == self._index      or self._maj_3rd_candidate == self._index) or
                    (self._min_3rd_candidate == -1 and self._maj_3rd_candidate == -1 and len(self._note_set) > 1)):
                self.change_root(self._dom_4th_candidate)

    def filter(self) -> dict:
        if self.find_maxima():
            self.find_spacial_profile()
            self.find_intervals()
            self.find_relative_dominant()
            self.find_3rds()
            self.analyze_intervals()
        return { 'root': self._tonic, 'third': self._tense}
