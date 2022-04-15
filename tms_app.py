from concurrent.futures import thread
import sys
import time
from pyqtgraph.Qt import QtCore, QtWidgets
import numpy as np
import pyqtgraph as pg
from datetime import datetime
import os
import csv
from collections import deque
import threading

# C:\Users\lhcub\anaconda3\envs\newdelsys\Lib\site-packages\qt5_applications\Qt\bin\designer.exe
import clr

clr.AddReference("resources/DelsysAPI")
clr.AddReference("System.Collections")
from QT.main_window import Ui_MainWindow
from Aero import AeroPy
from System import Int32
from System.Collections.Generic import List

from AeroPy.DataManager import DataKernel

key = "***REMOVED***"
license = '***REMOVED***'


import functools
import time

def timer(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        tic = time.perf_counter()
        value = func(*args, **kwargs)
        toc = time.perf_counter()
        elapsed_time = toc - tic
        # print(f"Elapsed time: {elapsed_time:0.6f} seconds")
        return value
    return wrapper_timer

class App(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(App, self).__init__(parent)
        self.setupUi(self)

        # Delsys
        self.base = AeroPy()
        self.DataHandler = DataKernel(self.base)

        self.canvas = pg.GraphicsLayoutWidget()
        self.canvas_layout.addWidget(self.canvas)
        self.browse_btn.clicked.connect(self.choose_folder)
        self.data_start_btn.clicked.connect(self.start_collection)
        self.channel_combo.currentIndexChanged.connect(self.change_channel)
        self.aux_sync_btn.clicked.connect(self.sync_signal)
        # self.actionExit.triggered.connect(self.closeEvent)
        #  line plot
        self.live_plot_itm = self.canvas.addPlot()
        self.live_plot = self.live_plot_itm.plot(pen="y")
        self.live_plot_itm.setLabel("bottom", "Time", "s")
        self.live_plot_itm.setLabel("left", "Voltage", "V")
        self.live_plot_itm.setYRange(-0.0015, 0.0015, padding=0)
        self.live_plot_itm.showGrid(x = True, y = True)

        self.freeze_plot_itm = self.canvas.addPlot()
        self.freeze_plot = self.freeze_plot_itm.plot(pen="y")
        self.freeze_plot_itm.setLabel("bottom", "Time", "ms")
        self.freeze_plot_itm.showGrid(x = True, y = True)
        self.freeze_plot_itm.setLabel("left", "Voltage", "V")

        #### Set Data  #####################
        # TODO: figure out a fixed time frame, and transform to seconds
        self.emg_sample_rate = 1926
        self.data_len = self.emg_sample_rate * 10
        self.frozen_data_len = int(round(self.emg_sample_rate / 10))
        self.frozen_data = deque(maxlen=self.frozen_data_len)
        # FIXME: figure out the sample time steps
        self.frozen_x = (
            np.linspace(0, self.frozen_data_len - 1, self.frozen_data_len)
            / self.emg_sample_rate
            * 1000
        )  # ms
        self.x = np.linspace(0, self.data_len - 1, self.data_len) / self.emg_sample_rate
        self.y_plot = np.full([self.data_len, 2], np.nan)
        self.is_saving_data = False
        self.saving_data_path = None
        self.file = None
        self.idx = 0
        self.selected_channel = 0

        self.counter = 0
        self.fps = 0.0
        self.initial_time = time.time()
        self.last_update = time.time()

        # Configure Delsys
        self.sensors_found = 0
        self.started_streaming = False
        t1 = threading.Thread(target=self.initialize_delsys)
        t1.start()
    
    def initialize_delsys(self):
        self.connect()
        self.scan()
        time.sleep(2)
        self.start_stream()
        self.started_streaming = True

    def choose_folder(self):
        dialog = QtWidgets.QFileDialog()
        folder_path = dialog.getExistingDirectory(None, "Select Folder")
        self.folder_in.setText(folder_path)

    def sync_signal(self):
        frozen_values = np.array(self.frozen_data.copy())
        print(np.min(frozen_values))
        self.freeze_plot.setData(self.frozen_x, frozen_values[:, self.selected_channel])

    def start_collection(self):
        if not self.is_saving_data:
            now = datetime.now()
            self.saving_data_path = f"{self.folder_in.text()}/{self.pat_code_in.text()}_{self.side_combo.currentText()}_{now.strftime('%Y%m%d_%H%M%S')}.csv"
            os.makedirs(os.path.dirname(self.saving_data_path), exist_ok=True)
            self.file = open(self.saving_data_path, "w+", newline="")
            self.writer = csv.writer(self.file)
            self.writer.writerow(["chan_1", "chan_2"])
            # self.file.write("timestamp,chan_1,chan_2\n")
            self.is_saving_data = True

            # Change color and text of button
            self.data_start_btn.setStyleSheet("background-color : yellow")
            self.data_start_btn.setText("Stop collection")
        else:
            self.file.close()
            self.is_saving_data = False
            self.data_start_btn.setStyleSheet("background-color : green")
            self.data_start_btn.setText("Start saving data")

    def change_channel(self, new_channel):
        self.selected_channel = new_channel

    def connect(self):
        self.base.ValidateBase(key, license, "RF")
    
    def scan(self):
        f = self.base.ScanSensors().Result
        self.nameList = self.base.ListSensorNames()
        self.sensors_found = len(self.nameList)
        if self.sensors_found == 0:
            sys.exit("No sensors found")

        self.base.ConnectSensors()
    
    def streaming(self):
        """This is the data processing thread"""
        self.emg_queue = deque()
        while self.pauseFlag is False:
            val = self.DataHandler.processData(self.emg_queue)
            if len(self.emg_queue) > 0:
                self.process_new_data(self.emg_queue.popleft())
                
                # print(self.emg_queue.popleft())
        print(self.DataHandler.getPacketCount())
    
    def start_stream(self):
        self.pauseFlag = False
        newTransform = self.base.CreateTransform("raw")
        index = List[Int32]()

        self.base.ClearSensorList()

        for i in range(self.sensors_found):
            selectedSensor = self.base.GetSensorObject(i)
            self.base.AddSensortoList(selectedSensor)
            index.Add(i)

        self.sampleRates = [[] for i in range(self.sensors_found)]
        self.base.StreamData(index, newTransform, 2)

        self.dataStreamIdx = []
        idxVal = 0
        for i in range(self.sensors_found):
            selectedSensor = self.base.GetSensorObject(i)
            for channel in range(len(selectedSensor.TrignoChannels)):
                self.sampleRates[i].append(
                    (
                        selectedSensor.TrignoChannels[channel].SampleRate,
                        selectedSensor.TrignoChannels[channel].Name,
                    )
                )
                if "EMG" in selectedSensor.TrignoChannels[channel].Name:
                    self.dataStreamIdx.append(idxVal)
                idxVal += 1
        print(self.dataStreamIdx)

        t1 = threading.Thread(target=self.streaming)
        t1.start()


    def stop_stream(self):
        self.base.StopData()
        self.pauseFlag = True

    def process_new_data(self, data):
        new_data = np.asarray(data, dtype=object)[
                tuple([self.dataStreamIdx])
            ]
        new_data = np.vstack(new_data).T / 1000
        if self.idx + new_data.shape[0] > self.data_len:
            self.idx = 0
            self.y_plot = np.full([self.data_len, 2], np.nan)
        self.y_plot[self.idx : self.idx + new_data.shape[0], :] = new_data
        self.frozen_data.extend(new_data.tolist())
        self.idx += new_data.shape[0] + 1

        if self.is_saving_data:
            self.writer.writerows(new_data.tolist())

    @timer
    def _update_plot(self):
        # self.img.setImage(self.data)
        self.live_plot.setData(self.x, self.y_plot[:, self.selected_channel])

        now = time.time()
        dt = now - self.last_update
        if dt <= 0:
            dt = 0.000000000001
        fps2 = 1.0 / dt
        self.last_update = now
        self.fps = self.fps * 0.9 + fps2 * 0.1
        tx = "Mean Frame Rate:  {fps:.3f} FPS".format(fps=self.fps)
        self.fps_label.setText(tx)
        # QtCore.QTimer.singleShot(1, self._update)
        self.counter += 1
    
    def closeEvent(self, event):
        if self.started_streaming:
            self.stop_stream()



if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    thisapp = App()
    thisapp.show()
    # timer = pg.QtCore.QTimer()
    # timer.timeout.connect(thisapp._update_data)
    # timer.start(5)
    timer2 = pg.QtCore.QTimer()
    timer2.timeout.connect(thisapp._update_plot)
    timer2.start(40)
    sys.exit(app.exec_())
