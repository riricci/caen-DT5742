from flask import Flask, send_file
from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from set_digitizer import configure_digitizer, convert_dictionaries_to_data_frame
import pandas as pd
import plotly.express as px
from pathlib import Path
import uproot
import os
import time
import threading

# Initial Configuration
THRESHOLD = -0.5
DATA_DIR = Path(__file__).parent / "data"
OUTPUT_HTML = DATA_DIR / "live_waveform_plot.html"
OUTPUT_TXT = DATA_DIR / "waveforms.txt"
OUTPUT_ROOT = DATA_DIR / "waveforms.root"
STOP_ACQUISITION = False
current_event = 0  # Global variable to track the current event number

# Ensure the data folder exists
DATA_DIR.mkdir(exist_ok=True)

# Flask App
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

# def save_waveforms_to_root(data, filename):
#     """Save data in ROOT format, separated by event."""
#     if data.empty:
#         print("WARNING: No data to save to ROOT.")
#         return

#     # Use 'update' to append data without overwriting
#     with uproot.update(filename) as root_file:
#         for event, group in data.groupby('n_event'):
#             tree_data = {
#                 "Time_s": group["Time (s)"].to_numpy(),
#                 "Amplitude_V": group["Amplitude (V)"].to_numpy()
#             }

#             # Save data under a unique key for the event
#             root_file[f"Event_{event}"] = tree_data

#     print(f"Waveforms saved to ROOT file: {filename}")

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
def data_acquisition_and_processing(digitizer):
    global STOP_ACQUISITION, current_event
    while not STOP_ACQUISITION:
        try:
            print("Acquiring data from digitizer...")
            with digitizer:
                time.sleep(0.5)
                waveforms = digitizer.get_waveforms()
                print(waveforms)

            if not waveforms:
                print("WARNING: No waveforms acquired. Retrying...")
                continue

            # Convert data into DataFrame
            data = convert_dictionaries_to_data_frame(waveforms)

            # Update the 'n_event' index with the current event number
            data = data.reset_index()  # Reset existing index
            data['n_event'] = current_event  # Assign the current event number
            data = data.set_index(['n_event', 'n_channel'])  # Reassign the index

            # Increment the event counter
            current_event += 1

            # Filter only the data from channel CH0
            ch0_data = data.loc[(slice(None), 'CH0'), :]
            ch1_data = data.loc[(slice(None), 'CH1'), :]

            # Apply threshold filter
            ch0_data_above_threshold = ch0_data[ch0_data['Amplitude (V)'] > THRESHOLD]
            ch1_data_above_threshold = ch1_data[ch1_data['Amplitude (V)'] > THRESHOLD]

            #if not ch0_data_above_threshold.empty:
                # Save the filtered data in TXT and ROOT formats
                #save_waveforms_to_txt(ch0_data_above_threshold, OUTPUT_TXT)
                # save_waveforms_to_root(ch0_data_above_threshold, OUTPUT_ROOT)

            # Combine CH0 data and trigger data for the plot
            trigger_data = data.loc[(slice(None), 'trigger_group_1'), :]
            combined_data = pd.concat([ch0_data_above_threshold, ch1_data_above_threshold, trigger_data])

            # Generate HTML plot
            generate_html_plot(combined_data, OUTPUT_HTML)

            print(f"Processed {current_event} events.")

        except Exception as e:
            print(f"Error during acquisition or processing: {e}")

# Main Script
if __name__ == '__main__':
    # Configure the digitizer
    digitizer = CAEN_DT5742_Digitizer(LinkNum=0)
    print('Connected with:', digitizer.idn)
    configure_digitizer(digitizer)

    # Start the data acquisition thread
    acquisition_thread = threading.Thread(target=data_acquisition_and_processing, args=(digitizer,))
    acquisition_thread.daemon = True
    acquisition_thread.start()

    # Start the Flask server
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=8050)
