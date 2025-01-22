import sys
import time
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QLabel
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
from datetime import datetime
from pathlib import Path
from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from digitizer_example_1 import configure_digitizer, convert_dicitonaries_to_data_frame
from baseline import extract_baseline_from_channel

# Initial Configuration
THRESHOLD = -0.5
DATA_DIR = Path(__file__).parent / "data"
STOP_ACQUISITION = False
current_event = 0  # Global variable to track the current event number   

# Ensure the data folder exists
DATA_DIR.mkdir(exist_ok=True)

# Functions for saving and processing data
def save_waveforms_to_txt(data, filename):
    """Save data in TXT format with a unique event name."""
    if data.empty:
        return

    with open(filename, 'a') as f:  # 'a' to append new data
        for event, group in data.groupby(level='n_event'):
            f.write(f"# Event {event}\n")
            reordered_group = group[['Time (s)', 'Amplitude (V)']]
            reordered_group.to_csv(f, index=False, header=True, sep='\t')
            f.write("\n")

# Data acquisition function
def data_acquisition_and_processing(digitizer, output_txt, update_plot_callback, update_event_button_callback):
    """Handles data acquisition, processing, and GUI updates."""
    global STOP_ACQUISITION, current_event
    while not STOP_ACQUISITION:
        try:
            with digitizer:
                time.sleep(0.5)
                waveforms = digitizer.get_waveforms(True, False)
                print(waveforms)
                # baseline = extract_baseline_from_channel(digitizer, 0) # baseline from CH0
                # if baseline is not None:
                #     print(f"Baseline for CH{0} BEFORE acquisition: {baseline}")
                # else:
                #     print(f"Failed to extract baseline for CH{0}.")

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

            # Filter data for CH0 and apply the threshold
            ch0_data = data.loc[(slice(None), 'CH0'), :]
            ch1_data = data.loc[(slice(None), 'CH1'), :]
            ch0_data_above_threshold = ch0_data[ch0_data['Amplitude (V)'] > THRESHOLD]
            ch1_data_above_threshold = ch1_data[ch1_data['Amplitude (V)'] > THRESHOLD]

            #if not ch0_data_above_threshold.empty:
                #save_waveforms_to_txt(ch0_data_above_threshold, output_txt)

            # Combine CH0 data and trigger data for the plot
            trigger_data = data.loc[(slice(None), 'trigger_group_1'), :]
            combined_data = pd.concat([ch0_data_above_threshold, ch1_data_above_threshold, trigger_data])
            # Update the plot
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
                    group['Amplitude (V)'],
                    label=f"Event {n_event}, {n_channel}",
                    linestyle='-',
                    marker='.',
                    markersize=4
                )

        self.ax.set_title("CAEN Digitizer Waveform")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude (V)")

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

        # Buttons for acquisition control
        self.start_button = QPushButton("Start Acquisition", self)
        self.start_button.clicked.connect(self.start_gui_acquisition)

        self.stop_button = QPushButton("Stop Acquisition", self)
        self.stop_button.clicked.connect(self.stop_gui_acquisition)

        # Button to display the number of events acquired
        self.event_button = QPushButton("Acquired 0 events", self)
        self.event_button.setEnabled(False)  # Disable interaction
        self.event_button.setStyleSheet("color: white; font-size: 16px; background-color: #333;")

        # Layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.stop_button)
        self.layout.addWidget(self.event_button)

        # Canvas for the plot
        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        self.layout.addWidget(self.canvas)

        # Main container
        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

    def start_gui_acquisition(self):
        """Starts the data acquisition process."""
        global STOP_ACQUISITION, current_event
        STOP_ACQUISITION = False
        current_event = 0  # Reset event counter
        print("Starting acquisition...")

        # Generate a unique file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_txt = DATA_DIR / f"waveforms_{timestamp}.txt"

        # Configure the digitizer
        digitizer = CAEN_DT5742_Digitizer(LinkNum=0)
        print('Connected with:', digitizer.idn)
        configure_digitizer(digitizer)

        # # experimental - channel baseline analysis
        # baseline = extract_baseline_from_channel(digitizer, 0) # baseline from CH0
        
        # if baseline is not None:
        #     print(f"Baseline for CH{0} BEFORE acquisition: {baseline}")
        # else:
        #     print(f"Failed to extract baseline for CH{0}.")

        # Start the acquisition thread
        acquisition_thread = threading.Thread(
            target=data_acquisition_and_processing,
            args=(digitizer, output_txt, self.update_plot, self.update_event_button)
        )
        acquisition_thread.daemon = True
        acquisition_thread.start()

    def stop_gui_acquisition(self):
        """Stops the data acquisition process."""
        global STOP_ACQUISITION
        STOP_ACQUISITION = True
        print("Stopping acquisition...")

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
