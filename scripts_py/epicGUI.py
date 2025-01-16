import sys
import threading
import time
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from digitizer_example_1 import configure_digitizer, convert_dicitonaries_to_data_frame
from pathlib import Path

# Global Variables
STOP_ACQUISITION = False
current_event = 0
THRESHOLD = -0.5
DATA_DIR = Path(__file__).parent / "data"
OUTPUT_HTML = DATA_DIR / "live_waveform_plot.html"
OUTPUT_TXT = DATA_DIR / "waveforms.txt"

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
            data = data.reset_index()
            data['n_event'] = current_event
            data = data.set_index(['n_event', 'n_channel'])

            # Increment the event counter
            current_event += 1

            # Filter data for CH0 and apply threshold
            ch0_data = data.loc[(slice(None), 'CH0'), :]
            ch0_data_above_threshold = ch0_data[ch0_data['Amplitude (V)'] > THRESHOLD]

            # Save the filtered data to TXT
            save_waveforms_to_txt(ch0_data_above_threshold, output_txt)

            # Generate HTML plot
            generate_html_plot(ch0_data_above_threshold, OUTPUT_HTML)

            print(f"Processed {current_event} events.")

        except Exception as e:
            print(f"Error during acquisition or processing: {e}")

# Save waveforms to TXT
def save_waveforms_to_txt(data, filename):
    """Save data in TXT format with a unique event name."""
    if data.empty:
        print("WARNING: No data to save to TXT.")
        return

    with open(filename, 'a') as f:
        for event, group in data.groupby(level='n_event'):
            f.write(f"# Event {event}\n")
            reordered_group = group[['Time (s)', 'Amplitude (V)']]
            reordered_group.to_csv(f, index=False, header=True, sep='\t')
            f.write("\n")
    print(f"Waveforms saved to TXT file: {filename}")

# Generate HTML plot with Plotly
def generate_html_plot(data, output_path):
    import plotly.express as px
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

# GUI Class with Qt
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Data Acquisition GUI")
        self.setGeometry(100, 100, 800, 600)

        # Layout
        self.layout = QVBoxLayout()

        # Start and Stop Buttons
        self.start_button = QPushButton('Start Acquisition')
        self.stop_button = QPushButton('Stop Acquisition')
        self.start_button.clicked.connect(self.start_acquisition)
        self.stop_button.clicked.connect(self.stop_acquisition)

        # Add buttons to layout
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.stop_button)

        # WebEngineView to display the plot
        self.webview = QWebEngineView()
        self.layout.addWidget(self.webview)

        # Set central widget
        self.central_widget = QWidget()
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

        # Initialize Flask thread
        self.flask_thread = threading.Thread(target=self.run_flask)
        self.flask_thread.daemon = True
        self.flask_thread.start()

        self.show()

    def start_acquisition(self):
        """Start the acquisition and processing thread"""
        global STOP_ACQUISITION, current_event
        STOP_ACQUISITION = False
        current_event = 0  # Reset event count

        # Create a new TXT file for the acquisition
        output_txt = DATA_DIR / f"waveforms_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        print(f"Started acquisition. Data will be saved to: {output_txt}")

        # Configure digitizer
        digitizer = CAEN_DT5742_Digitizer(LinkNum=0)
        configure_digitizer(digitizer)

        # Start the data acquisition thread
        acquisition_thread = threading.Thread(target=data_acquisition_and_processing, args=(digitizer, output_txt))
        acquisition_thread.daemon = True
        acquisition_thread.start()

    def stop_acquisition(self):
        """Stop the data acquisition"""
        global STOP_ACQUISITION
        STOP_ACQUISITION = True
        print("Acquisition stopped.")

    def run_flask(self):
        """Run the Flask server to serve the plot."""
        from flask import Flask, send_file
        app = Flask(__name__)

        @app.route('/')
        def serve_plot():
            """Serve the HTML plot"""
            if OUTPUT_HTML.exists():
                return send_file(OUTPUT_HTML, mimetype='text/html')
            return "Plot not generated yet. Please wait and refresh.", 404

        app.run(host='0.0.0.0', port=8050)

    def update_plot(self):
        """Load the plot in WebEngineView"""
        self.webview.setUrl(f"http://127.0.0.1:8050")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
