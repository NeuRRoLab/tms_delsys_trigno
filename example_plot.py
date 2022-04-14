import sys
import time
from pyqtgraph.Qt import QtCore, QtWidgets
import numpy as np
import pyqtgraph as pg


class App(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(App, self).__init__(parent)

        #### Create Gui Elements ###########
        self.mainbox = QtWidgets.QWidget()
        self.setCentralWidget(self.mainbox)
        self.mainbox.setLayout(QtWidgets.QVBoxLayout())

        self.canvas = pg.GraphicsLayoutWidget()
        self.mainbox.layout().addWidget(self.canvas)

        self.label = QtWidgets.QLabel()
        self.mainbox.layout().addWidget(self.label)

        #  line plot
        self.live_plot_itm = self.canvas.addPlot()
        self.live_plot = self.live_plot_itm.plot(pen="y")

        self.freeze_plot_itm = self.canvas.addPlot()
        self.freeze_plot = self.freeze_plot_itm.plot(pen="y")

        #### Set Data  #####################
        self.data_len = 10000
        self.new_data_len = 20
        self.x = np.linspace(0, self.data_len - 1, self.data_len) * 0.01
        self.y = np.full([self.data_len], np.nan)
        self.idx = 0

        self.counter = 0
        self.fps = 0.0
        self.initial_time = time.time()
        self.last_update = time.time()

    def _update_data(self):
        new_data_len = 5
        new_data = np.random.random(new_data_len) - 0.5
        if self.idx + new_data_len >= self.data_len:
            self.idx = 0
            self.y = np.full([self.data_len], np.nan)
        self.y[self.idx : self.idx + new_data_len] = new_data
        self.idx += new_data_len + 1

    def _update_plot(self):
        # self.img.setImage(self.data)
        self.live_plot.setData(self.x, self.y)

        now = time.time()
        dt = now - self.last_update
        if dt <= 0:
            dt = 0.000000000001
        fps2 = 1.0 / dt
        self.last_update = now
        self.fps = self.fps * 0.9 + fps2 * 0.1
        tx = "Mean Frame Rate:  {fps:.3f} FPS".format(fps=self.fps)
        self.label.setText(tx)
        # QtCore.QTimer.singleShot(1, self._update)
        self.counter += 1


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    thisapp = App()
    thisapp.show()
    timer = pg.QtCore.QTimer()
    timer.timeout.connect(thisapp._update_data)
    timer.start(5)
    timer2 = pg.QtCore.QTimer()
    timer2.timeout.connect(thisapp._update_plot)
    timer2.start(40)
    sys.exit(app.exec_())
