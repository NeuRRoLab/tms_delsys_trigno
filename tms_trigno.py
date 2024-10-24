import csv
import os
import sys
import threading
import time
from collections import deque
from datetime import datetime

import clr
import numpy as np
from PyQt5 import QtWidgets
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets

from os.path import expanduser

clr.AddReference("lib/DelsysAPI")
clr.AddReference("System.Collections")
import functools
import time

from Aero import AeroPy
from System import Int32
from System.Collections.Generic import List

from AeroPy.DataManager import DataKernel
from QT.main_window import Ui_MainWindow

exception_happened = False


# Read license and key
with open("config/key", mode="r", encoding="utf-8-sig") as key_file:
    key = key_file.read()
with open("config/license.lic", mode="r", encoding="utf-8-sig") as license_file:
    license = license_file.read()

# Aux function to determine frames per second
def timer(func):
    """Auxiliar function used to determine execution time of function func.

    Args:
        func (function): function to try

    Returns:
        float: execution time of function
    """

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        if exception_happened:
            return
        tic = time.perf_counter()
        value = func(*args, **kwargs)
        toc = time.perf_counter()
        elapsed_time = toc - tic
        #print(f"Elapsed time: {elapsed_time:0.6f} seconds")
        return value

    return wrapper_timer

class App(QtWidgets.QMainWindow, Ui_MainWindow):
    """App that manages both the GUI and the streaming of data"""

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

        try:
            self.aux_sync_btn.clicked.connect(self.sync_signal)
        except:
            self.console_msg.setText("Console: Could not sync.")

        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self.scan_sensors)
        # Live plot (left)
        self.live_plot_itm = self.canvas.addPlot()
        self.live_plot = self.live_plot_itm.plot(pen="y")
        self.live_plot_itm.setLabel("bottom", "Time", "s")
        self.live_plot_itm.setLabel("left", "Voltage", "V")
        self.live_plot_itm.setYRange(-5.3, 5.3, padding=0)
        self.live_plot_itm.showGrid(x=True, y=True)
        # Freeze plot (right)
        self.freeze_plot_itm = self.canvas.addPlot()
        self.freeze_plot = self.freeze_plot_itm.plot(pen="y")
        self.freeze_plot_itm.setLabel("bottom", "Time", "ms")
        self.freeze_plot_itm.showGrid(x=True, y=True)
        self.freeze_plot_itm.setLabel("left", "Voltage", "V")
        self.ppvoltage_label.setText(f"0.0")

        # Get Threshold
        self.threshold_btn.clicked.connect(self.get_thresh)

        # Get freeze bounds
        self.freezeOK.clicked.connect(self.get_freeze)

        #### Set Data  #####################
        # TODO: modify sample rate according to application
        
        self.emg_sample_rate = 1925.9259033203125
        seconds_to_capture = 10
        self.data_len = int(round(self.emg_sample_rate * seconds_to_capture))

        # Whether we are saving data right now or not
        self.is_saving_data = False
        self.saving_data_path = None
        self.file = None
        # Current index in left plot. Resets to zero after it reaches the limit
        self.idx = 0
        # Channel being shown
        self.selected_channel = 0
        # Whether threshold is user set
        self.setThresh = False
        self.thresholdCanChange = True
        # Whether frames are user set
        self.setFrame = False
        self.framesCanChange = True

        self.console_msg.setText("Console: Set threshold and frames BEFORE scanning.")

        self.counter = 0
        self.fps = 0.0
        self.initial_time = time.time()
        self.last_update = time.time()
        self.channelcount = 0
        self.pairnumber = 0
        # Configure Delsys
        self.sensors_found = 0
        self.started_streaming = False
        self.pauseFlag = False
        self.stim_ts = 0
        self.stim_collecting_data = False

    def get_freeze(self):


        if self.framesCanChange == True:
            self.console_msg.setText("Console: Freeze Frames set.")

            self.setFrame = True

            if self.setThresh == True:
                self.scan_btn.setEnabled(True)
            self.freezeStartFrame = float(self.freezeBegin.text())
            self.freezeEndFrame = float(self.freezeEnd.text())

            milliseconds_frozen = self.freezeEndFrame
            self.freeze_plot_itm.setXRange(0,self.freezeEndFrame, padding = 0)

            self.frozen_data_len = int(
                round(self.emg_sample_rate * milliseconds_frozen/1000)
            )

            self.frozen_data = deque(maxlen=self.frozen_data_len)
            self.frozen_x = (
                np.linspace(0, self.frozen_data_len - 1, self.frozen_data_len)
                / self.emg_sample_rate
                * 1000
            )  # ms
            
            # X axis represents time, and its spacing depends on the sample rate
            self.x = np.linspace(0, self.data_len - 1, self.data_len) / self.emg_sample_rate
            self.y_plot = np.full([self.data_len, 4], np.nan)
        else:
            self.console_msg.setText("Console: Frames cannot be changed after sensors are connected.")
        
        

    def get_thresh(self):
        self.setThresh = True
        if self.setFrame == True:
            self.scan_btn.setEnabled(True)

        self.thresh = float(self.threshold.text())
        if self.thresholdCanChange == True:
            self.console_msg.setText("Console: Threshold set.")
        else:
            self.console_msg.setText("Console: Threshold cannot be changed after sensors are connected.")

    def scan_sensors(self):
        # Initialize Delsys and start streaming
        self.t1 = threading.Thread(target=self.initialize_delsys)
        self.t1.start()

    def initialize_delsys(self):
        """Initializes Delsys and then starts streaming"""
        self.console_msg.setText("Console: Scanning...")

        try:
            self.connect()
            self.scan()
            
            self.console_msg.setText("Console: Connecting to sensors")

                # Wait for it to connect and scan properly
            time.sleep(4)
            self.start_stream()
            self.console_msg.setText("Console: Connected to sensors")
            # Flag to establish that we started the streaming
            self.started_streaming = True

            # disable threshold change
            self.threshold.setEnabled(False)
            self.thresholdCanChange = False
            self.freezeOK.setEnabled(False)
            self.framesCanChange = False
            # Disable scanning again
            self.scan_btn.setEnabled(False)

        except:
        #     #self.scan_error()

            print("Sensors were not connected")
            self.console_msg.setText("Console: Could not connect. Restart application.")
            self.scan_btn.setEnabled(False)
            self.started_streaming = False


    def choose_folder(self):
        """Choose folder dialog; runs when user clicks on the 'Browse' button."""
        # dlog = QtWidgets.QFileDialog()
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(None, "Select Folder", expanduser("~"), options=QtWidgets.QFileDialog.DontUseNativeDialog)
        # # Set the folder path in the GUI
        self.folder_in.setText(folder_path)

    def sync_signal(self):
        """Runs when there is a detected TMS sync signal. Sets the data for the frozen (right) plot"""
        frozen_values = np.array(self.frozen_data.copy())
        self.freeze_plot.setData(self.frozen_x, frozen_values[:, self.selected_channel])
        print("Sync Channel "+ str(self.selected_channel))
        ppvoltage = (
            np.max(frozen_values[:, self.selected_channel])
            - np.min(frozen_values[:, self.selected_channel]) * 1e6
        )
        self.ppvoltage_label.setText(f"{ppvoltage:.1f}")

    def start_collection(self):
        """Starts the data saving. Changes a few GUI elements to represent that the data is being saved"""
        if not self.is_saving_data:
            now = datetime.now()
            self.saving_data_path = f"{self.folder_in.text()}/{self.pat_code_in.text()}_{self.side_combo.currentText()}_{now.strftime('%Y%m%d_%H%M%S')}.csv"
            os.makedirs(os.path.dirname(self.saving_data_path), exist_ok=True)
            try:
                self.file = open(self.saving_data_path, "w+", newline="")
            except:
                self.console_msg.setText("Console: Could not save. Set output directory.")
            self.writer = csv.writer(self.file)
            
            headers = []
            headers.append("stim")
            for chan in range(self.sensors_found-1):
                if chan == 0:
                    headers.append("EMG_2")
                elif chan == 1:
                    headers.append("EMG_1")
                elif chan == 2:
                    headers.append("EMG_4")
                else:
                    headers.append("UNKNOWN")

            self.writer.writerow(headers)
            self.is_saving_data = True

            # Change color and text of button
            self.data_start_btn.setStyleSheet("background-color : yellow")
            self.data_start_btn.setText("Stop collection")
        else:
            # If already saving data, we stop the collection and change the necessary elements
            self.file.close()
            self.is_saving_data = False
            self.data_start_btn.setStyleSheet("background-color : green")
            self.data_start_btn.setText("Start saving data")

    def change_channel(self, new_channel):
        """Switch channels in left plot

        Args:
            new_channel (str): new channel to display
        """
        self.selected_channel = new_channel

    def connect(self):
        """Validates the Trigno Lite base using the license and key"""
        try:
            self.base.ValidateBase(key, license, "RF")
        except Exception as e:
            global exception_happened
            exception_happened = True

    def scan(self):
        """Scans for available sensors"""
        self.base.ScanSensors().Result
        self.nameList = self.base.GetSensorNames()
        self.sensors_found = len(self.nameList)
        print("Found sensors:" , self.sensors_found)
        if self.sensors_found == 0:
            self.pauseFlag = True

            # sys.exit("No sensors found")

        # Connect to found sensors
        self.base.SelectAllSensors()

    def streaming(self):
        """This is the data processing thread"""
        self.emg_queue = deque()
        while not self.pauseFlag:
            self.DataHandler.processData(self.emg_queue)
            # If any values available, go process them
            if len(self.emg_queue) > 0:
                self.process_new_data(self.emg_queue.popleft())

    def start_stream(self):
        """Gets the EMG (and Sync) channels from the sensors and starts streaming"""
        newTransform = self.base.CreateTransform("raw")
        index = List[Int32]()
        self.base.ClearSensorList()

        modes = [
            "EMG plus accelerometer (+/- 16g), +/-5.5mV, 20-450Hz",
            "EMG plus accelerometer (+/- 16g), +/-5.5mV, 20-450Hz",
            "SIG raw x4 (1926 Hz-148Hz), Low Bandwidth",
            "EMG plus accelerometer (+/- 16g), +/-5.5mV, 20-450Hz",
        ]

        for i in range(self.sensors_found):
            selectedSensor = self.base.GetSensorObject(i)
            self.base.SetSampleMode(i, modes[i])
            self.base.AddSensortoList(selectedSensor)
            index.Add(i)

        # curMode = self.base.GetSampleMode()
        # print(curMode)
        self.sampleRates = [[] for i in range(self.sensors_found)]
        # Start streaming the data from the sensors
        # self.base.StreamData(index, newTransform, 2)
        self.base.Configure()
        self.base.Start()

        self.dataStreamIdx = []
        idxVal = 0
        for i in range(self.sensors_found):
            selectedSensor = self.base.GetSensorObject(i)
            for channel in range(len(selectedSensor.TrignoChannels)):
                # Get sample rates
                self.sampleRates[i].append(
                    (
                        selectedSensor.TrignoChannels[channel].SampleRate,
                        selectedSensor.TrignoChannels[channel].Name,
                    )
                )
                # EMG corresponds to an EMG channel
                # Analog 1 corresponds to the Sync channel
                if (
                    "EMG" in selectedSensor.TrignoChannels[channel].Name
                    or "Analog 1" in selectedSensor.TrignoChannels[channel].Name
                ):
                    if "EMG" in selectedSensor.TrignoChannels[channel].Name:
                        # Add the corresponding text to the channel dropdown menu
                        self.channel_combo.addItem(
                            f"Channel {len(self.dataStreamIdx) + 1}"
                        )
                    else:
                        self.tmsChannel = len(self.dataStreamIdx)
                        self.channel_combo.addItem(f"TMS Stim")
                    self.dataStreamIdx.append(idxVal)
                idxVal += 1
        self.num_channels = len(self.dataStreamIdx)
        self.channel_combo.setCurrentIndex(0)

        # Switch position of TMS Stim and Channel 1
        item_1 = self.channel_combo.itemText(0)
        item_3 = self.channel_combo.itemText(2)
        self.channel_combo.removeItem(2)
        self.channel_combo.removeItem(0)
        self.channel_combo.insertItem(0, item_3)
        self.channel_combo.insertItem(2, item_1)
        self.tmsChannel = 0


        print("Sample rates")
        print(self.sampleRates)
        # Start consuming data
        self.t1 = threading.Thread(target=self.streaming)
        self.t1.start()

    def stop_stream(self):
        """Stop the stream"""
        self.base.Stop()
        self.pauseFlag = True

    def process_new_data(self, data):
        """Data processing method. Receives input from sensors and updates the necessary variables

        Args:
            data (List): output from the processing queue
        """
        # Convert to array to facilitate indexing the useful data
        new_data = np.asarray(data, dtype=object)[tuple([self.dataStreamIdx])]
        # print(new_data, end="\n")

        # Check array length
        lengths = [len(arr) for arr in new_data]
        if(len(set(lengths))) != 1:
            print("Data Different Length, Autofilled")
            max_len = max(lengths)
            for i, arr in enumerate(new_data):
                if(len(arr) < max_len):
                    new_data[i] = np.pad(arr, (0, max_len - len(arr)), mode='edge')

        new_data = (np.vstack(new_data).T / 1000 * 454.545)
        # If we reached the limit on the left plot, reset index
        if self.idx + new_data.shape[0] > self.data_len:
            self.idx = 0
            self.y_plot = np.full([self.data_len, 4], np.nan)

        if self.stim_collecting_data:
            # How many datapoints are we missing
            missing_elements = self.frozen_data.maxlen - len(self.frozen_data)
            if missing_elements > 0:
                # Add at most missing_elements elements to the frozen data
                self.frozen_data.extend(new_data[:missing_elements, :].tolist())
            # If we already have enough data, call the sync signal
            if len(self.frozen_data) == self.frozen_data.maxlen:
                self.stim_collecting_data = False
                self.sync_signal()

        if self.setThresh == False:
            self.thresh = 0.03
            check = np.max(abs(new_data[:,self.tmsChannel])) > self.thresh     
        else:
            check = np.max(abs(new_data[:,self.tmsChannel])) > abs(self.thresh)

        # Check if a stim happened
        if not self.stim_collecting_data and check == True:
            self.stim_ts = time.time()
            tmp = abs(new_data[:,self.tmsChannel]) - np.abs(self.thresh)
            # Modify timestamp by index of first sample that went below threshold
            if self.signalType.currentText() == "Rising":
                sign_changes = (
                    np.where((np.sign(tmp[:-1]) != np.sign(tmp[1:])) & ((tmp[:-1]) < (tmp[1:])))[0] + 1
                ) 
            else:
                sign_changes = (
                    np.where((np.sign(tmp[:-1]) != np.sign(tmp[1:])) & ((tmp[:-1]) > (tmp[1:])))[0] + 1
                ) 
            self.frozen_data = deque(maxlen=self.frozen_data_len)
            try:
                self.frozen_data.extend(new_data[sign_changes[0]:, :].tolist())
                
                self.stim_collecting_data = True
            except:
                self.console_msg.setText("Preparing sensors")
                

        self.y_plot[self.idx : self.idx + new_data.shape[0], :] = new_data
        # Add one to the left plot idx
        self.idx += new_data.shape[0] + 1

        if self.is_saving_data:
            # Save data if necessary
            self.writer.writerows(new_data.tolist())

    @timer
    def _update_plot(self):
        """Update left (live) plot with the newest data"""
        # TODO: figure out how to make this more efficient, to achieve higher fps
        # TODO: for some reason, this function runs at a constant frequency only if we have the timer printing time.
        if not self.started_streaming:
            return
        # Set the plot data
        self.live_plot.setData(self.x, self.y_plot[:, self.selected_channel])
        # Calculate fps
        now = time.time()
        dt = now - self.last_update
        if dt <= 0:
            dt = 0.000000000001
        fps2 = 1.0 / dt
        self.last_update = now
        self.fps = self.fps * 0.9 + fps2 * 0.1
        tx = "Mean Frame Rate:  {fps:.3f} FPS".format(fps=self.fps)
        self.fps_label.setText(tx)
        self.counter += 1

    def closeEvent(self, event):
        """Captures the window close event and stops the streaming"""
        if self.started_streaming:
            self.stop_stream()

    def PipelineState_Callback(self):
        return self.base.GetPipelineState()

    def Connect_Callback(self):
        """Callback to connect to the base"""
        self.base.ValidateBase(key, license)

    def Pair_Callback(self):
        return self.base.PairSensor(self.pair_number)

    def CheckPairStatus(self):
        return self.base.CheckPairStatus()

    def CheckPairComponentAdded(self):
        return self.base.CheckPairComponentAdded()

    def Scan_Callback(self):
        """Callback to tell the base to scan for any available sensors"""
        try:
            f = self.base.ScanSensors().Result
        except Exception as e:
            print("Python demo attempt another scan...")
            time.sleep(1)
            self.Scan_Callback()

        self.all_scanned_sensors = self.base.GetScannedSensorsFound()
        print("Sensors Found:\n")
        for sensor in self.all_scanned_sensors:
            print("(" + str(sensor.PairNumber) + ") " +
                sensor.FriendlyName + "\n" +
                sensor.Configuration.ModeString + "\n")

        self.SensorCount = len(self.all_scanned_sensors)
        for i in range(self.SensorCount):
            self.base.SelectSensor(i)

        return self.all_scanned_sensors


    def Start_Callback(self, start_trigger, stop_trigger):
        """Callback to start the data stream from Sensors"""
        self.start_trigger = start_trigger
        self.stop_trigger = stop_trigger

        configured = self.ConfigureCollectionOutput()
        if configured:
            #(Optional) To get YT data output pass 'True' to Start method
            self.base.Start(self.collection_data_handler.streamYTData)
            self.collection_data_handler.threadManager(self.start_trigger, self.stop_trigger)

    def ConfigureCollectionOutput(self):
        if not self.start_trigger:
            self.collection_data_handler.pauseFlag = False

        self.collection_data_handler.DataHandler.packetCount = 0
        self.collection_data_handler.DataHandler.allcollectiondata = [[]]

        # Pipeline Armed when TrigBase.Configure already called.
        # This if block allows for sequential data streams without reconfiguring the pipeline each time.
        # Reset output data structure before starting data stream again
        if self.base.GetPipelineState() == 'Armed':
            for i in range(len(self.channelobjects)):
                self.collection_data_handler.DataHandler.allcollectiondata.append([])
            return True


        # Pipeline Connected when sensors have been scanned in sucessfully.
        # Configure output data using TrigBase.Configure and pass args if you are using a start and/or stop trigger
        elif self.base.GetPipelineState() == 'Connected':
            self.channelcount = 0
            self.base.Configure(self.start_trigger, self.stop_trigger)
            configured = self.base.IsPipelineConfigured()
            if configured:
                self.channelobjects = []
                self.plotCount = 0
                self.emgChannelsIdx = []
                globalChannelIdx = 0

                for i in range(self.SensorCount):

                    selectedSensor = self.base.GetSensorObject(i)
                    print("(" + str(selectedSensor.PairNumber) + ") " + str(selectedSensor.FriendlyName))

                    if len(selectedSensor.TrignoChannels) > 0:
                        print("--Channels")

                        for channel in range(len(selectedSensor.TrignoChannels)):
                            sample_rate = round(selectedSensor.TrignoChannels[channel].SampleRate, 3)
                            print("----" + selectedSensor.TrignoChannels[channel].Name + " (" + str(sample_rate) + " Hz)")
                            self.channelcount += 1
                            self.channelobjects.append(channel)
                            self.collection_data_handler.DataHandler.allcollectiondata.append([])

                            # NOTE: Plotting/Data Output: This demo does not plot non-EMG channel types such as
                            # accelerometer, gyroscope, magnetometer, and others. However, the data from channels
                            # that are excluded from plots are still available via output from PollData()

                            # ---- Plot EMG Channels
                            if "EMG" in selectedSensor.TrignoChannels[channel].Name:
                                self.emgChannelsIdx.append(globalChannelIdx)
                                self.plotCount += 1

                            # ---- Exclude non-EMG channels from plots
                            else:
                                pass

                            globalChannelIdx += 1

                if self.collection_data_handler.EMGplot:
                    self.collection_data_handler.EMGplot.initiateCanvas(None, None, self.plotCount, 1, 20000)

                return True
        else:
            return False

    def Stop_Callback(self):
        """Callback to stop the data stream"""
        self.collection_data_handler.pauseFlag = True
        self.base.Stop()
        print("Data Collection Complete")

    # ---------------------------------------------------------------------------------
    # ---- Helper Functions
    def getSampleModes(self, sensorIdx):
        """Gets the list of sample modes available for selected sensor"""
        sampleModes = self.base.AvailibleSensorModes(sensorIdx)
        return sampleModes

    def getCurMode(self, sensorIdx):
        """Gets the current mode of the sensors"""
        curModes = self.base.GetCurrentSensorMode(sensorIdx)
        return curModes

    def setSampleMode(self, curSensor, setMode):
        """Sets the sample mode for the selected sensor"""
        self.base.SetSampleMode(curSensor, setMode)


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    thisapp = App()
    thisapp.show()
    timer = pg.QtCore.QTimer()
    # Updates the plot at a 'fixed' frequency
    timer.timeout.connect(thisapp._update_plot)
    interval = 30  # ms
    timer.setInterval(interval)
    timer.start()
    sys.exit(app.exec_())