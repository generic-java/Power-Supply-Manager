import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.font_manager import FontProperties

from tkutils import *

MATPLOTLIB_TICKS = {
    "fontfamily": "Source Code Pro",
    "fontweight": "normal",
    "fontsize": 10
}

FONT = {
    "family": "Source Code Pro",
    "weight": "normal",
    "size": 10
}


class Graph(Thread):
    def __init__(self, master, dataCount: int, legend: list = []):
        super().__init__(daemon=True)
        self.font = FontProperties(fname="fonts\Source_Code_Pro\static\SourceCodePro-Regular.ttf")
        self._figure = plt.figure(figsize=(10, 5), facecolor=GRAY)
        self._ax = self._figure.add_subplot()
        self._ax.tick_params(colors=BLUE)
        self._ax.set_xlabel('Elapsed time', fontproperties=self.font, color=BLUE, labelpad=15)
        self._canvas = FigureCanvasTkAgg(self._figure, master=master)
        self._dataSeries = [[[], []]] * dataCount
        self._lineColors = ["orange", "green", "blue", "red", "yellow"]
        self._legend = legend
        self._lines = []
        self._refreshRequested = True
        for i in range(len(self._dataSeries)):
            if i < len(legend):
                label = legend[i]
            else:
                label = None
            self._lines.append(self._ax.plot([], [], label=label, color=self._lineColors[i])[0])
            if legend:
                plt.legend(loc="upper right", prop=self.font)
        self.start()

    def addTo(self, index, x, y):
        if type(x)==list:
            for xValue in x:
                self._dataSeries[index][0].append(xValue)
        else:
            self._dataSeries[index][0].append(x)
        if type(y)==list:
            for yValue in y:
                self._dataSeries[index][1].append(yValue)
        else:
            self._dataSeries[index][1].append(y)
        self._refreshRequested = True

    def wipe(self, index):
        self._dataSeries[index] = [[], []]

    def wipeAll(self):
        for i in range(len(self._dataSeries)):
            self.wipe(i)

    def clear(self):
        self._ax.cla()

    def getWidget(self):
        return self._canvas.get_tk_widget()

    def run(self):
        while True:
            try:
                if self._refreshRequested:
                    for i in range(len(self._dataSeries)):
                        self._lines[i].set_xdata(self._dataSeries[i][0])
                        self._lines[i].set_ydata(self._dataSeries[i][1])
                        self._ax.autoscale_view()
                        self._ax.relim()
                        for label in self._ax.get_xticklabels():
                            label.set_fontproperties(self.font)
                        for label in self._ax.get_yticklabels():
                            label.set_fontproperties(self.font)
                        plt.grid(True)
                    self._canvas.draw()
                self._refreshRequested = False
            finally:
                time.sleep(0.5)
