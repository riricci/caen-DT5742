import sys
import time
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pandas as pd
from datetime import datetime
from pathlib import Path
from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from digitizer_example_1 import configure_digitizer, convert_dicitonaries_to_data_frame

# Initial Configuration
THRESHOLD = -0.5
DATA_DIR = Path(__file__).parent / "data"
STOP_ACQUISITION = False
current_event = 0  # Global variable to track the current event number
current_frequency = 5000  # Default sampling frequency in MHz

# Ensure the data folder exists
DATA_DIR.mkdir(exist_ok=True)

# Data acquisition function
def data_acquisition_and_processing(digitizer, output_txt, update_plot_callback, update_event_button_callback):
    """Handles data acquisition, processing, and GUI updates."""
    global STOP_ACQUISITION, current_event
    while not STOP_ACQUISITION:
        try:
            with digitizer:
                time.sleep(0.5)
                waveforms = digitizer.get_waveforms(True, True)

            if not waveforms:
                continue

            # Convert data into DataFrame
            data = convert_dicitonaries_to_data_frame(waveforms)
            data = data.reset_index()
            data['n_event'] = current_event
            data = data.set_index(['n_event', 'n_channel'])

            current_event += 1

            # Update event count in the GUI
            update_event_button_callback(current_event)

            # Filter data for CH0 and CH1
            ch0_data = data.loc[(slice(None), 'CH0'), :]
            ch1_data = data.loc[(slice(None), 'CH1'), :]

            # Combine CH0 and CH1 data for the plot
            combined_data = pd.concat([ch0_data, ch1_data])
            update_plot_callback(combined_data)

        except Exception as e:
            print(f"Error during acquisition: {e}")

# Matplotlib Canvas for Plotting
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)

    def plot_data(self, data):
        """Plots the data on the canvas."""
        self.ax.clear()

        # Set dark style
        self.fig.patch.set_facecolor('#121212')
        self.ax.set_facecolor('#121212')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('white')

        # Enable grid
        self.ax.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.7)

        if not data.empty:
            for (n_event, n_channel), group in data.groupby(level=['n_event', 'n_channel']):
                self.ax.plot(
                    group['Time (s)'],
                    group['Amplitude (ADCu)'],
                    label=f"Event {n_event}, {n_channel}",
                    linestyle='-',
                    marker='.',
                    markersize=4
                )

        self.ax.set_title("CAEN Digitizer Waveform")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude (ADCu)")

        # Increase tick frequency
        self.ax.xaxis.set_major_locator(MaxNLocator(nbins=10))
        self.ax.yaxis.set_major_locator(MaxNLocator(nbins=10))

        # Customize legend
        legend = self.ax.legend(loc='upper right', fontsize='small', facecolor='black', edgecolor='white')
        if legend:
            for text in legend.get_texts():
                text.set_color('white')

        self.draw()

# PyQt MainWindow with start/stop buttons and plot
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CAEN Digitizer Interface")
        self.setGeometry(100, 100, 800, 600)

        # Digitizer instance
        self.digitizer = CAEN_DT5742_Digitizer(LinkNum=0)
        print('Connected with:', self.digitizer.idn)

        # Buttons for acquisition control
        self.start_button = QPushButton("Start Acquisition", self)
        self.start_button.clicked.connect(self.start_gui_acquisition)

        self.stop_button = QPushButton("Stop Acquisition", self)
        self.stop_button.clicked.connect(self.stop_gui_acquisition)

        # Buttons for sampling frequency
        self.freq_buttons = []
        for freq in [5, 2.5, 1, 0.75]:  # Frequencies in GHz
            btn = QPushButton(f"{freq} GHz", self)
            btn.clicked.connect(lambda _, f=freq: self.set_sampling_frequency(f))
            btn.setEnabled(True)  # Enable by default
            self.freq_buttons.append(btn)

        # Button to display the number of events acquired
        self.event_button = QPushButton("Acquired 0 events", self)
        self.event_button.setEnabled(False)
        self.event_button.setStyleSheet("color: white; font-size: 16px; background-color: #333;")

        # Layouts
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        for btn in self.freq_buttons:
            control_layout.addWidget(btn)

        self.layout = QVBoxLayout()
        self.layout.addLayout(control_layout)
        self.layout.addWidget(self.event_button)

        # Canvas for the plot
        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        self.layout.addWidget(self.canvas)

        # Add the Matplotlib navigation toolbar for zoom and pan
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)

        # Main container
        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

    def set_sampling_frequency(self, freq):
        """Set the sampling frequency of the digitizer."""
        global current_frequency
        current_frequency = int(freq * 1000)  # Convert GHz to MHz
        if self.digitizer:
            self.digitizer.set_sampling_frequency(MHz=current_frequency)
        print(f"Sampling frequency set to {freq} GHz ({current_frequency} MHz)")

    def start_gui_acquisition(self):
        """Starts the data acquisition process."""
        global STOP_ACQUISITION, current_event
        STOP_ACQUISITION = False
        current_event = 0
        print("Starting acquisition...")

        # Generate a unique file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_txt = DATA_DIR / f"waveforms_{timestamp}.txt"

        # Configure the digitizer
        # self.digitizer = CAEN_DT5742_Digitizer(LinkNum=0)
        # print('Connected with:', self.digitizer.idn)
        self.digitizer.reset()  # Soft reset the digitizer
        configure_digitizer(self.digitizer)
        self.digitizer.set_sampling_frequency(MHz=current_frequency)  # Apply the current frequency

        # Disable frequency buttons
        for btn in self.freq_buttons:
            btn.setEnabled(False)

        # Start the acquisition thread
        acquisition_thread = threading.Thread(
            target=data_acquisition_and_processing,
            args=(self.digitizer, output_txt, self.update_plot, self.update_event_button)
        )
        acquisition_thread.daemon = True
        acquisition_thread.start()

    def stop_gui_acquisition(self):
        """Stops the data acquisition process."""
        global STOP_ACQUISITION
        STOP_ACQUISITION = True
        print("Stopping acquisition...")

        # Enable frequency buttons
        for btn in self.freq_buttons:
            btn.setEnabled(True)

    def update_plot(self, data):
        """Updates the plot with new data."""
        if not data.empty:
            first_event = data.index.get_level_values('n_event').min()
            data = data.loc[(first_event, slice(None)), :]
        self.canvas.plot_data(data)

    def update_event_button(self, num_events):
        """Updates the event counter button."""
        self.event_button.setText(f"Acquired {num_events} events")

# Main function
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
