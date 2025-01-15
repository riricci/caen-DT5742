import sys
import time
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from flask import Flask, send_file
from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from digitizer_example_1 import configure_digitizer, convert_dicitonaries_to_data_frame
import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import datetime

# Initial Configuration
THRESHOLD = -0.5
DATA_DIR = Path(__file__).parent / "data"
OUTPUT_HTML = DATA_DIR / "live_waveform_plot.html"
STOP_ACQUISITION = False
current_event = 0  # Global variable to track the current event number

# Ensure the data folder exists
DATA_DIR.mkdir(exist_ok=True)

# Flask App
def create_flask_app():
    app = Flask(__name__)

    @app.route('/')
    def serve_plot():
        """Serve the HTML file of the plot."""
        if OUTPUT_HTML.exists():
            return send_file(OUTPUT_HTML, mimetype='text/html')
        return "Plot not generated yet. Please wait and refresh.", 404

    @app.route('/stop')
    def stop_acquisition():
        """Safely stop data acquisition."""
        global STOP_ACQUISITION
        STOP_ACQUISITION = True
        return "Data acquisition stopped.", 200

    return app

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

def generate_html_plot(data, output_path):
    """Generate an interactive plot and save it in HTML format."""
    fig = px.line(
        title='CAEN Digitizer Waveform and Trigger',
        data_frame=data.reset_index(),
        x='Time (s)',
        y='Amplitude (V)',
        color='n_channel',
        markers=True,
        facet_row='n_event',
    )
    fig.write_html(output_path, include_plotlyjs='cdn')
    print(f"Plot saved to {output_path}")

# Data acquisition function
def data_acquisition_and_processing(digitizer, output_txt):
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

            # Generate HTML plot
            generate_html_plot(combined_data, OUTPUT_HTML)

            print(f"Processed {current_event} events.")

        except Exception as e:
            print(f"Error during acquisition or processing: {e}")

# PyQt MainWindow with start/stop buttons
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CAEN Digitizer Interface")
        self.setGeometry(100, 100, 300, 150)

        self.start_button = QPushButton("Start Acquisition", self)
        self.start_button.clicked.connect(self.start_acquisition)

        self.stop_button = QPushButton("Stop Acquisition", self)
        self.stop_button.clicked.connect(self.stop_acquisition)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.stop_button)

        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

    def start_acquisition(self):
        global STOP_ACQUISITION
        STOP_ACQUISITION = False
        print("Starting acquisition...")

        # Generate a unique file name based on the current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_txt = DATA_DIR / f"waveforms_{timestamp}.txt"

        # Configure the digitizer
        digitizer = CAEN_DT5742_Digitizer(LinkNum=0)
        print('Connected with:', digitizer.idn)
        configure_digitizer(digitizer)

        # Start the data acquisition thread
        acquisition_thread = threading.Thread(target=data_acquisition_and_processing, args=(digitizer, output_txt))
        acquisition_thread.daemon = True
        acquisition_thread.start()

    def stop_acquisition(self):
        global STOP_ACQUISITION
        STOP_ACQUISITION = True
        print("Stopping acquisition...")

# Main function
def main():
    app = QApplication(sys.argv)

    # Create Flask app separately
    flask_app = create_flask_app()

    # Start the Flask server in a separate thread
    flask_thread = threading.Thread(target=flask_app.run, kwargs={'host': '0.0.0.0', 'port': 8050})
    flask_thread.daemon = True
    flask_thread.start()

    # Start the Qt Application
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
