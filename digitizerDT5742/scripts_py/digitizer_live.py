from flask import Flask, send_file
from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from digitizer_example_1 import configure_digitizer, convert_dicitonaries_to_data_frame
import pandas as pd
import plotly.express as px
from pathlib import Path
import time
import threading

# Percorso del file HTML
output_path = Path(__file__).parent / 'live_plot.html'

# Flask App
app = Flask(__name__)

@app.route('/')
def serve_plot():
    """Serve il file HTML del plot."""
    if output_path.exists():
        return send_file(output_path, mimetype='text/html')
    else:
        return "Plot not generated yet. Please wait a moment and refresh the page.", 404

# Funzione per generare il plot HTML
def generate_html_plot(data, output_path):
    # Crea il grafico con Plotly Express
    fig = px.line(
        title='CAEN Digitizer Live Plot',
        data_frame=data.reset_index(),
        x='Time (s)',
        y='Amplitude (V)',
        color='n_channel',
        facet_row='n_event',
        markers=True,
    )
    fig.write_html(output_path, include_plotlyjs='cdn')
    print(f"Plot updated and saved to {output_path}")
    
# Funzione per acquisire dati e aggiornare il plot
def data_acquisition_loop(digitizer):
    while True:
        try:
            print("Acquiring data from digitizer...")
            with digitizer:
                time.sleep(1)  # Aspetta per acquisire eventi
                waveforms = digitizer.get_waveforms()

            if len(waveforms) == 0:
                print("WARNING: No waveforms acquired.")
                continue

            # Converti i dati in DataFrame
            data = convert_dicitonaries_to_data_frame(waveforms)

            # Genera il file HTML
            generate_html_plot(data, output_path)

            # Aspetta prima del prossimo aggiornamento
            print("Waiting 5 seconds before next update...")
            time.sleep(5)

        except Exception as e:
            print(f"Error during data acquisition: {e}")

if __name__ == '__main__':
    # Configura il digitizer
    digitizer = CAEN_DT5742_Digitizer(LinkNum=0)
    print('Connected with:', digitizer.idn)
    configure_digitizer(digitizer)
    digitizer.set_max_num_events_BLT(3)

    # Avvia il thread per l'acquisizione dei dati
    acquisition_thread = threading.Thread(target=data_acquisition_loop, args=(digitizer,))
    acquisition_thread.daemon = True
    acquisition_thread.start()

    # Avvia il server Flask
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=8050)
