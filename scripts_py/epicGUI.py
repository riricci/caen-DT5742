import sys
import time
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from digitizer_example_1 import configure_digitizer, convert_dicitonaries_to_data_frame
from pathlib import Path
import pandas as pd
import threading

# Setup Directory and File for Saving Data
DATA_DIR = Path(__file__).parent / "data"
OUTPUT_TXT = DATA_DIR / "test_waveform.txt"
THRESHOLD = -0.5
STOP_ACQUISITION = False
current_event = 0

# Ensure the data folder exists
DATA_DIR.mkdir(exist_ok=True)

# Function to save data to a file
def save_waveform_to_txt(data, filename):
    if data.empty:
        print("WARNING: No data to save.")
        return

    with open(filename, 'a') as f:  # Open in append mode
        for event, group in data.groupby(level='n_event'):
            f.write(f"# Event {event}\n")
            reordered_group = group[['Time (s)', 'Amplitude (V)']]
            reordered_group.to_csv(f, index=False, header=True, sep='\t')
            f.write("\n")
    print(f"Waveform saved to {filename}")

# Acquisition Function
def acquire_waveform(digitizer):
    global current_event

    try:
        print("Acquiring data from digitizer...")
        
        # Acquire waveform data
        with digitizer:
            time.sleep(0.5)  # Adjust timing as needed
            waveforms = digitizer.get_waveforms()

        if waveforms:
            print("Waveform acquired successfully.")
            
            # Convert data to DataFrame
            data = convert_dicitonaries_to_data_frame(waveforms)
            
            # Update 'n_event' index
            data = data.reset_index()
            data['n_event'] = current_event
            data = data.set_index(['n_event', 'n_channel'])
            
            # Increment event counter
            current_event += 1
            
            # Filter by threshold for CH0
            ch0_data = data.loc[(slice(None), 'CH0'), :]
            ch0_data_above_threshold = ch0_data[ch0_data['Amplitude (V)'] > THRESHOLD]
            
            if not ch0_data_above_threshold.empty:
                save_waveform_to_txt(ch0_data_above_threshold, OUTPUT_TXT)

        else:
            print("No waveforms acquired.")
    
    except Exception as e:
        print(f"Error during acquisition: {e}")

# Qt GUI for controlling the acquisition
class AcquisitionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Waveform Acquisition')

        # Layout setup
        layout = QVBoxLayout()

        # Start and Stop Acquisition Buttons
        self.start_button = QPushButton('Start Acquisition', self)
        self.stop_button = QPushButton('Stop Acquisition', self)

        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)

        # Connect buttons to their respective methods
        self.start_button.clicked.connect(self.start_acquisition)
        self.stop_button.clicked.connect(self.stop_acquisition)

        self.setLayout(layout)
        self.show()

    def start_acquisition(self):
        """Start the acquisition process."""
        global STOP_ACQUISITION
        STOP_ACQUISITION = False
        
        # Configure digitizer (assuming digitizer is connected)
        self.digitizer = CAEN_DT5742_Digitizer(LinkNum=0)
        print("Digitizer connected:", self.digitizer.idn)
        configure_digitizer(self.digitizer)
        
        # Start the acquisition in a separate thread
        print("Starting acquisition thread...")
        self.acquisition_thread = threading.Thread(target=self.run_acquisition)
        self.acquisition_thread.daemon = True
        self.acquisition_thread.start()

    def run_acquisition(self):
        """Run the data acquisition loop."""
        global STOP_ACQUISITION

        while not STOP_ACQUISITION:
            acquire_waveform(self.digitizer)
            time.sleep(1)  # Control the speed of acquisition (1 second delay)

    def stop_acquisition(self):
        """Stop the acquisition process."""
        global STOP_ACQUISITION
        STOP_ACQUISITION = True
        print("Acquisition stopped.")

# Main function to run the app
def main():
    app = QApplication(sys.argv)
    window = AcquisitionWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
