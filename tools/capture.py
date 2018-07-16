from numpy import add, arange, average, abs, empty, fromstring, fft, int16, log10, multiply, ndarray, reshape, split
from pyaudio import PyAudio, paInt16
from threading import Thread
from .log import logger


class AudioCapture:
    def __init__(self):
        self._bitrate = 48100
        self._buffer_size = 8192
        self._sec_to_capture = 0.1
        self._exiting = False
        self._running = False
        self.has_captured = False
        logger.info('AudioCapture settings:')
        self._capture_buffers = int(self._sec_to_capture * self._bitrate / self._buffer_size)
        if not self._capture_buffers:
            self._capture_buffers = 1
        self._capture_samples = int(self._buffer_size * self._capture_buffers) # == sec_to_capture * bitrate
        self._sec_per_period = 1.0 / self._bitrate
        self.open_input_stream()
        self._x_buffer = arange(self._buffer_size) * self._sec_per_period
        self._x_values = arange(self._capture_buffers * self._buffer_size) * self._sec_per_period
        self._x_audio = empty((self._capture_buffers * self._buffer_size), dtype=int16)
        self._capture_thread = Thread(target=self.record)
        logger.info('  bitrate: %d, buffer_size: %d', self._bitrate, self._buffer_size)
        logger.info('  capture_buffers: %d, capture_samples: %d, sec_per_period: %g',
                    self._capture_buffers, self._capture_samples, self._sec_per_period)

    def open_input_stream(self, purge=False):
        if purge:
            self._audio_signal.close(self._input_stream)
            self._audio_signal.terminate()
            del self._audio_signal
        self._audio_signal = PyAudio()
        self._input_stream = self._audio_signal.open(
            format=paInt16,
            channels=1,
            rate=self._bitrate,
            input=True,
            frames_per_buffer=self._buffer_size
        )

    def close(self):
        if self._running:
            self.stop()
            self._capture_thread.join()
        # self._audio_signal.close(self._input_stream)
        self._audio_signal.terminate()

    def get_audio(self) -> ndarray:
        try:
            str_audio = self._input_stream.read(self._buffer_size)
        except IOError as e:
            logger.error('audio err: %s, %s', e, e.errno)
            self.open_input_stream(purge=True)
            str_audio = '\x00' * 2 * self._buffer_size
        return fromstring(str_audio, dtype=int16)

    def record(self, forever=True):
        while not self._exiting:
            self._running = True
            for i in range(self._capture_buffers):
                _lower = int(i * self._buffer_size)
                _upper = int((i + 1) * self._buffer_size)
                self._x_audio[_lower:_upper] = self.get_audio()
            self.has_captured = True
            if not forever:
                break
        self._running = False

    def start(self):
        self._capture_thread.start()

    def stop(self):
        self._exiting = True

    def downsample(self, data: ndarray, scale: int) -> ndarray:
        window_overlap = len(data) % scale
        if window_overlap:
            data = data[:-window_overlap]
        data = reshape(data, (len(data) / scale, scale))
        data = average(data, 1)
        return data

    def fft(self, data=None, slice=10, log_scale=False, db_gain=1e-2, single_tail=False) -> tuple:
        if data is None:
            data = self._x_audio.flatten()
        self.has_captured = False
        _buffer_size = self._buffer_size
        if single_tail:
            _buffer_size = float(self._buffer_size / 2)
            lhs, rhs = split( abs( fft.fft(data) ), 2)
            _y = add(lhs, rhs[::-1])
        else:
            _y = abs( fft.fft(data) )
        _x = arange(_buffer_size, dtype=float)
        if log_scale:
            _y = multiply(20, log10(_y))
        if slice:
            i = int(_buffer_size / slice)
            _y = _y[:i]
            _x = _x[:i] * float(self._bitrate / self._buffer_size)
        if db_gain:
            _y = float(db_gain) * _y
        return _x, _y
