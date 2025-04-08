# Imports
from PyQt6 import QtWidgets
import matplotlib
matplotlib.use('QtAgg')  # Set the backend before other matplotlib imports
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as Canvas


# Matplotlib canvas class to create figure
class MplCanvas(Canvas):
    def __init__(self):
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)  # Use super() for cleaner initialization
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding
        )
        self.updateGeometry()

# Matplotlib widget
class MplWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)   # Use super() for cleaner initialization
        self.canvas = MplCanvas()  # Create canvas object
        self.vbl = QtWidgets.QVBoxLayout()  # Set box for plotting
        self.vbl.addWidget(self.canvas)
        self.setLayout(self.vbl)
