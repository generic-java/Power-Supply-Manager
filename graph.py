import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.font_manager import FontProperties

from tkutils import *


class Graph(Thread):
    def __init__(self, master, data_count: int, legend=None):
        super().__init__(daemon=True)
        if legend is None:
            legend = []
        self.font = FontProperties(fname=APPLICATION_FONT_PATH)
        self._figure = plt.figure(figsize=(10, 5), facecolor=GRAY)
        self._ax = self._figure.add_subplot()
        self._ax.tick_params(colors=BLUE)
        self._ax.set_xlabel('Elapsed time', fontproperties=self.font, color=BLUE, labelpad=15)
        self._canvas = FigureCanvasTkAgg(self._figure, master=master)
        self._data_series = [[[], []]] * data_count
        self._line_colors = ["orange", "green", "blue", "red", "yellow"]
        self._legend = legend
        self._lines = []
        self._refresh_requested = True
        for i in range(len(self._data_series)):
            if i < len(legend):
                label = legend[i]
            else:
                label = None
            self._lines.append(self._ax.plot([], [], label=label, color=self._line_colors[i])[0])
            if legend:
                plt.legend(loc="upper right", prop=self.font)
        self.start()

    def add_to(self, index, x, y):
        if type(x) is list:
            for xValue in x:
                self._data_series[index][0].append(xValue)
        else:
            self._data_series[index][0].append(x)
        if type(y) is list:
            for yValue in y:
                self._data_series[index][1].append(yValue)
        else:
            self._data_series[index][1].append(y)
        self._refresh_requested = True

    def wipe(self, index):
        self._data_series[index] = [[], []]

    def wipe_all(self):
        for i in range(len(self._data_series)):
            self.wipe(i)

    def clear(self):
        self._ax.cla()

    def get_widget(self):
        return self._canvas.get_tk_widget()

    def run(self):
        while True:
            try:
                if self._refresh_requested:
                    for i in range(len(self._data_series)):
                        self._lines[i].set_xdata(self._data_series[i][0])
                        self._lines[i].set_ydata(self._data_series[i][1])
                        self._ax.autoscale_view()
                        self._ax.relim()
                        for label in self._ax.get_xticklabels():
                            label.set_fontproperties(self.font)
                        for label in self._ax.get_yticklabels():
                            label.set_fontproperties(self.font)
                        plt.grid(True)
                    self._canvas.draw()
                self._refresh_requested = False
            finally:
                time.sleep(0.5)
