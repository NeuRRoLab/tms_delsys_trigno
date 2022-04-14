from concurrent.futures import thread

import clr

clr.AddReference("resources/DelsysAPI")
clr.AddReference("System.Collections")
import sys
import threading
import time
from collections import deque

import numpy as np
from Aero import AeroPy
from System import Int32
from System.Collections.Generic import List

from AeroPy.DataManager import DataKernel

key = "***REMOVED***"
license = '***REMOVED***'


class TrignoBase:
    def __init__(self):
        self.base = AeroPy()
        self.DataHandler = DataKernel(self.base)
        self.plotter = LivePlot(2, ["1", "2"])

        t = threading.Thread(target=self.plotter.run)
        t.start()

    def connect(self):
        self.base.ValidateBase(key, license, "RF")

    def scan(self):
        f = self.base.ScanSensors().Result
        self.nameList = self.base.ListSensorNames()
        self.SensorsFound = len(self.nameList)
        if self.SensorsFound == 0:
            self.plotter.stop = True
            sys.exit("No sensors found")

        self.base.ConnectSensors()
        return self.nameList

    def streaming(self):
        """This is the data processing thread"""
        self.emg_queue = deque()
        while self.pauseFlag is False:
            val = self.DataHandler.processData(self.emg_queue)
            if len(self.emg_queue) > 0:
                incData = self.emg_queue.popleft()
                outData = np.asarray(incData, dtype=object)[
                    tuple([self.dataStreamIdx])
                ].tolist()
                self.plotter.handle_new_data(outData)
                # print(self.emg_queue.popleft())
        print(self.DataHandler.getPacketCount())

    def start_stream(self):
        self.pauseFlag = False
        newTransform = self.base.CreateTransform("raw")
        index = List[Int32]()

        self.base.ClearSensorList()

        for i in range(self.SensorsFound):
            selectedSensor = self.base.GetSensorObject(i)
            self.base.AddSensortoList(selectedSensor)
            index.Add(i)

        self.sampleRates = [[] for i in range(self.SensorsFound)]
        self.base.StreamData(index, newTransform, 2)

        self.dataStreamIdx = []
        idxVal = 0
        for i in range(self.SensorsFound):
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

        # time.sleep(3)
        # self.stop_stream()

    def stop_stream(self):
        self.base.StopData()
        self.pauseFlag = True
        self.plotter.stop = True


if __name__ == "__main__":
    tb = TrignoBase()
    tb.connect()
    tb.scan()
    time.sleep(5)
    try:
        tb.start_stream()
        while True:
            time.sleep(1)
    finally:
        tb.stop_stream()
