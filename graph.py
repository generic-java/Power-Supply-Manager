import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from tkutils import *

MATPLOTLIB_TICKS = {
    "fontfamily": "Microsoft New Tai Lue",
    "fontweight": "normal",
    "fontsize": 10
}


class Graph(Thread):
    def __init__(self, master, dataCount: int):
        super().__init__(daemon=True)
        plt.xticks(**MATPLOTLIB_TICKS)
        plt.yticks(**MATPLOTLIB_TICKS)
        self._figure = plt.figure(figsize=(10, 5), facecolor=GRAY)
        self._ax = self._figure.add_subplot()
        self._ax.tick_params(colors=BLUE)
        self._canvas = FigureCanvasTkAgg(self._figure, master=master)
        self.dataSeries = [[[], []]] * dataCount
        self.lines = []
        for _ in self.dataSeries:
            self.lines.append(self._ax.plot([], [])[0])
        self.start()

    def addTo(self, index, x, y):
        if type(x)==list:
            for xValue in x:
                self.dataSeries[index][0].append(xValue)
        else:
            self.dataSeries[index][0].append(x)
        if type(y)==list:
            for yValue in y:
                self.dataSeries[index][1].append(yValue)
        else:
            self.dataSeries[index][1].append(y)

    def wipe(self, index):
        self.dataSeries[index] = [[], []]

    def wipeAll(self):
        for i in range(len(self.dataSeries)):
            self.wipe(i)

    def clear(self):
        self._ax.cla()

    def getWidget(self):
        return self._canvas.get_tk_widget()

    def run(self):
        while True:
            try:
                for i in range(len(self.dataSeries)):
                    self.lines[i].set_xdata(self.dataSeries[i][0])
                    self.lines[i].set_ydata(self.dataSeries[i][1])
                    self._ax.autoscale_view()
                    self._ax.relim()
                self._canvas.draw()
            finally:
                time.sleep(0.5)
