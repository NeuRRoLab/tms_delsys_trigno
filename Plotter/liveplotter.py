import time
from matplotlib import pyplot as plt
import numpy as np
import sys

from collections import deque


class LivePlot:
    FREQUENCY = 30

    def __init__(self, num_lines, labels):
        self.fig = None
        self.ax = None
        self.num_lines = num_lines
        self.lines = [None for _ in range(self.num_lines)]
        self.axbackground = None
        maxsize = 10000
        self.y = [deque(maxlen=maxsize) for _ in range(self.num_lines)]
        self.x = deque(maxlen=maxsize)
        self.first_time = None
        self.last_data_timestamp = None
        self.frequency = LivePlot.FREQUENCY
        self.labels = labels
        self.stop = False

    def init_process(self):
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        for i in range(self.num_lines):
            (l,) = self.ax.plot([], lw=2)
            self.lines[i] = l
        self.axbackground = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        self.fig.canvas.draw()
        plt.show(block=False)
        plt.legend(self.labels)
    
    def handle_new_data(self, data):
        """data is a list of lists of length num line"""
        if self.first_time is None:
            self.first_time = time.time()
            self.last_data_timestamp = time.time()
            return
        
        
        # We assume equal length on all new datapoints
        num_samples = len(data[0])
        time_since_last = time.time() - self.last_data_timestamp
        time_per_sample = time_since_last / num_samples

        self.x += (-self.first_time + self.last_data_timestamp + np.linspace(time_per_sample, time_since_last, num_samples)).tolist()
        print(min(self.x))
        for i in range(self.num_lines):
            self.y[i] += list(data[i])

            # Update lines
            self.lines[i].set_data(np.array(self.x), np.array(self.y[i]))
        self.ax.set_xlim(min(self.x), max(self.x))
        self.ax.set_ylim(np.min(self.y), np.max(self.y))

        self.last_data_timestamp = time.time()

    def run(self):
        self.init_process()
        try:
            while not self.stop:
                # self.fig.canvas.restore_region(self.axbackground)
                # self.ax.draw_artist(self.line1)
                # self.ax.draw_artist(self.line2)
                # self.fig.canvas.blit(self.ax.bbox)
                self.fig.canvas.draw()

                self.fig.canvas.flush_events()

        except KeyboardInterrupt:
            pass
