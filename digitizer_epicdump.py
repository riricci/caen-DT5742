from flask import Flask, send_file
from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from digitizer_example_1 import configure_digitizer, convert_dicitonaries_to_data_frame
import pandas as pd
import plotly.express as px
from pathlib import Path
import time
import threading
import os


# Percorsi dei file
output_path = Path(__file__).parent / 'live_waveform_and_trigger_plot.html'
output_txt = Path(__file__).parent / 'saved_waveforms.txt'

# Soglia di trigger (in Volt)
THRESHOLD = 0.5  # Valore arbitrario, da adattare alle esigenze

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

# Funzione per salvare le waveform buone in un file
def save_waveforms_to_txt(data, filename):
    """Salva le waveform sopra soglia in un file di testo (Time, Amplitude)."""
    absolute_path = os.path.abspath(filename)
    with open(absolute_path, 'a') as f:
        for event, group in data.groupby(level='n_event'):
            f.write(f"Event {event}:\n")
            reordered_group = group[['Time (s)', 'Amplitude (V)']]
            f.write(reordered_group.to_string(index=False, header=False))
            f.write("\n\n")
    print(f"Waveforms saved to {absolute_path}")


# Funzione per acquisire e plottare dati live
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

            # Converti i dati in DataFrame
            data = convert_dicitonaries_to_data_frame(waveforms)

            # Filtra i dati per CH0
            ch0_data = data.loc[(slice(None), 'CH0'), :]

            # Applica il filtro per la soglia
            ch0_data_above_threshold = ch0_data[ch0_data['Amplitude (V)'] > THRESHOLD]

            if not ch0_data_above_threshold.empty:
                # Salva gli eventi con waveform sopra soglia
                save_waveforms_to_txt(ch0_data_above_threshold, './waveforms_above_threshold.txt')

            # Combina waveform e trigger (facoltativo) per il plot
            # Combina waveform sopra soglia e trigger per il plot
            trigger_data = data.loc[(slice(None), 'trigger_group_1'), :]
            combined_data = pd.concat([ch0_data_above_threshold, trigger_data])

            # Genera il file HTML per il grafico live
            generate_html_plot(combined_data, output_path)


            # Aspetta prima del prossimo aggiornamento
            time.sleep(1)

        except Exception as e:
            print(f"Error during data acquisition or plotting: {e}")

if __name__ == '__main__':
    # Configura il digitizer
    digitizer = CAEN_DT5742_Digitizer(LinkNum=0)
    print('Connected with:', digitizer.idn)
    configure_digitizer(digitizer)

    # Avvia il thread per l'acquisizione dei dati e aggiornamento del plot
    acquisition_thread = threading.Thread(target=data_acquisition_and_plot, args=(digitizer,))
    acquisition_thread.daemon = True
    acquisition_thread.start()

    # Avvia il server Flask
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=8050)
