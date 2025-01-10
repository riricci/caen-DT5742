from flask import Flask, send_file
from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from digitizer_example_1 import configure_digitizer, convert_dicitonaries_to_data_frame
import pandas as pd
import plotly.express as px
from pathlib import Path
import time
import threading
import os

# still developing. 

# missing a STOP ACQUISITION function to safely end the data taking!! To be done.
# the basic configuration of the digitizer relays on digitizer_example_1 and 2.py. 
# See the function configure_digitizer in digitizer_example_1.py for details.

# Live plot file path
output_path = Path(__file__).parent / 'live_waveform_and_trigger_plot.html'
output_txt = Path(__file__).parent / 'saved_waveforms.txt'

# signal threshold (still absolute...to be fixed)
THRESHOLD = -0.05  

# Flask App
app = Flask(__name__)

@app.route('/')
def serve_plot():
    """Serve il file HTML del plot."""
    if output_path.exists():
        return send_file(output_path, mimetype='text/html')
    else:
        return "Plot not generated yet. Please wait a moment and refresh the page.", 404

# function to generate html plot
def generate_html_plot(data, output_path):
    """Genera il grafico e lo salva come HTML."""
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
    print(f"Plot updated and saved to {output_path}")

# Function to save waveform to txt file (to be studied)
def save_waveforms_to_txt(data, filename):
    """Saving waveform to txt file (Time, Amplitude)."""
    absolute_path = os.path.abspath(filename)
    with open(absolute_path, 'a') as f:
        for event, group in data.groupby(level='n_event'):
            f.write(f"Event {event}:\n")
            reordered_group = group[['Time (s)', 'Amplitude (V)']]
            f.write(reordered_group.to_string(index=False, header=False))
            f.write("\n\n")
    print(f"Waveforms saved to {absolute_path}") # not printing yet. to be fixed.


# Function to acquire and plot live data
def data_acquisition_and_plot(digitizer):
    while True:
        try:
            print("Acquiring one waveform from digitizer...")
            with digitizer:
                time.sleep(0.5)  # Aspetta per garantire l'acquisizione
                waveforms = digitizer.get_waveforms()

            if not waveforms:
                print("WARNING: No waveform acquired. Retrying...")
                continue

            # Data conversion to pandas data frames --> evaluate migration to ROOTDataFrames
            data = convert_dicitonaries_to_data_frame(waveforms)

            # Considerind only data from CHO
            ch0_data = data.loc[(slice(None), 'CH0'), :]

            # Filtering for threshold
            ch0_data_above_threshold = ch0_data[ch0_data['Amplitude (V)'] > THRESHOLD]

            if not ch0_data_above_threshold.empty:
                # Saving only events above threshold
                save_waveforms_to_txt(ch0_data_above_threshold, './waveforms_above_threshold.txt')

            # Combining waveform and trigger (optional) for the plot
            # Combining waveform (above thr) and trigger for the plot
            trigger_data = data.loc[(slice(None), 'trigger_group_1'), :]
            combined_data = pd.concat([ch0_data_above_threshold, trigger_data])

            # Generating html file for live plotting
            generate_html_plot(combined_data, output_path)


            # Waiting before next updat
            time.sleep(1)

        except Exception as e:
            print(f"Error during data acquisition or plotting: {e}")

if __name__ == '__main__':
    # Configuring digitizer
    digitizer = CAEN_DT5742_Digitizer(LinkNum=0)
    print('Connected with:', digitizer.idn)
    configure_digitizer(digitizer)

    # Srarting thread for data acquisition and live plotting
    acquisition_thread = threading.Thread(target=data_acquisition_and_plot, args=(digitizer,))
    acquisition_thread.daemon = True
    acquisition_thread.start()

    # Starting flask server
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=8050)
