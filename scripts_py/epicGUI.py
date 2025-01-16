import sys
import time
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
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

# Ensure the data folder exists
DATA_DIR.mkdir(exist_ok=True)

# Functions for saving and processing data
def save_waveforms_to_txt(data, filename):
    """Save data in TXT format with a unique event name."""
    if data.empty:
        print("WARNING: No data to save to TXT.")
        return

    with open(filename, 'a') as f:  # 'a' to append new data
        for event, group in data.groupby(level='n_event'):
            # Write the event with its number
            f.write(f"# Event {event}\n")
            reordered_group = group[['Time (s)', 'Amplitude (V)']]
            reordered_group.to_csv(f, index=False, header=True, sep='\t')
            f.write("\n")
    print(f"Waveforms saved to TXT file: {filename}")

# Data acquisition function
def data_acquisition_and_processing(digitizer, output_txt, update_plot_callback):
    global STOP_ACQUISITION, current_event
    while not STOP_ACQUISITION:
        try:
            print("Acquiring data from digitizer...")
            with digitizer:
                time.sleep(0.5)
                waveforms = digitizer.get_waveforms()

            if not waveforms:
                print("WARNING: No waveforms acquired. Retrying...")
                continue

            # Convert data into DataFrame
            data = convert_dicitonaries_to_data_frame(waveforms)

            # Update the 'n_event' index with the current event number
            data = data.reset_index()  # Reset existing index
            data['n_event'] = current_event  # Assign the current event number
            data = data.set_index(['n_event', 'n_channel'])  # Reassign the index

            # Increment the event counter
            current_event += 1

            # Filter only the data from channel CH0
            ch0_data = data.loc[(slice(None), 'CH0'), :]

            # Apply threshold filter
            ch0_data_above_threshold = ch0_data[ch0_data['Amplitude (V)'] > THRESHOLD]

            if not ch0_data_above_threshold.empty:
                # Save the filtered data in TXT format
                save_waveforms_to_txt(ch0_data_above_threshold, output_txt)

            # Combine CH0 data and trigger data for the plot
            trigger_data = data.loc[(slice(None), 'trigger_group_1'), :]
            combined_data = pd.concat([ch0_data_above_threshold, trigger_data])

            # Update the plot
            update_plot_callback(combined_data)

            print(f"Processed {current_event} events.")

        except Exception as e:
            print(f"Error during acquisition or processing: {e}")

# Matplotlib Canvas for Plotting
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)

    def plot_data(self, data):
        self.ax.clear()
        if not data.empty:
            for (n_event, n_channel), group in data.groupby(level=['n_event', 'n_channel']):
                self.ax.plot(
                    group['Time (s)'], 
                    group['Amplitude (V)'], 
                    label=f"Event {n_event}, {n_channel}", 
                    linestyle='', marker='.', markersize=4  # Smaller and more delicate markers
                )
        self.ax.set_title("CAEN Digitizer Waveform")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude (V)")
        self.ax.legend()
        self.draw()

# PyQt MainWindow with start/stop buttons and plot
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CAEN Digitizer Interface")
        self.setGeometry(100, 100, 800, 600)

        self.start_button = QPushButton("Start Acquisition", self)
        self.start_button.clicked.connect(self.start_acquisition)

        self.stop_button = QPushButton("Stop Acquisition", self)
        self.stop_button.clicked.connect(self.stop_acquisition)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.stop_button)

        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        self.layout.addWidget(self.canvas)

        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

    def start_acquisition(self):
        global STOP_ACQUISITION, current_event
        STOP_ACQUISITION = False
        current_event = 0  # Reset the event counter
        print("Starting acquisition...")

        # Generate a unique file name based on the current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_txt = DATA_DIR / f"waveforms_{timestamp}.txt"

        # Configure the digitizer
        digitizer = CAEN_DT5742_Digitizer(LinkNum=0)
        print('Connected with:', digitizer.idn)
        configure_digitizer(digitizer)

        # Start the data acquisition thread
        acquisition_thread = threading.Thread(
            target=data_acquisition_and_processing, 
            args=(digitizer, output_txt, self.update_plot)
        )
        acquisition_thread.daemon = True
        acquisition_thread.start()

    def stop_acquisition(self):
        global STOP_ACQUISITION
        STOP_ACQUISITION = True
        print("Stopping acquisition...")

    def update_plot(self, data):
        # Filter data for the first event only
        if not data.empty:
            first_event = data.index.get_level_values('n_event').min()
            data = data.loc[(first_event, slice(None)), :]
        self.canvas.plot_data(data)

# Main function
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
