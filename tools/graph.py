from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph import GraphicsWindow, setConfigOptions

from sys import flags

class PlotSignalWindow():
    def __init__(self, width=1000, height=600):
        # signal
        self.signal = dict()
        # setup window
        self.app = QtGui.QApplication([])
        self.win = GraphicsWindow(title="Plot Signal")
        self.win.resize(width, height)
        self.win.setWindowTitle('Plot Signal')
        # enable anti-aliasing
        setConfigOptions(antialias=True)
        self.canvas = self.win.addPlot(title="Fast Fourier Transform")
        # limit plot to 20Hz to 20kHz and clamp magnitude
        # self.canvas.setXRange(0, 20000)
        self.canvas.setYRange(0, 100000)

    def start(self):
        if (flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()

    def draw(self, name: str, _x, _y, pen='y'):
        if name in self.signal:
            self.signal[name].setData(_x, _y)
        else:
            self.signal[name] = self.canvas.plot(pen=pen)
