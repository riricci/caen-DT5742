from flask import Flask, send_file
from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from digitizer_example_1 import configure_digitizer, convert_dicitonaries_to_data_frame
import pandas as pd
import plotly.express as px
from pathlib import Path
import uproot
import os
import time
import threading

# Configurazione iniziale
THRESHOLD = -0.05
DATA_DIR = Path(__file__).parent / "data"
OUTPUT_HTML = DATA_DIR / "live_waveform_plot.html"
OUTPUT_TXT = DATA_DIR / "waveforms.txt"
OUTPUT_ROOT = DATA_DIR / "waveforms.root"
STOP_ACQUISITION = False

# Assicurati che la cartella per i dati esista
DATA_DIR.mkdir(exist_ok=True)

# Flask App
app = Flask(__name__)

@app.route('/')
def serve_plot():
    """Serve il file HTML del plot."""
    if OUTPUT_HTML.exists():
        return send_file(OUTPUT_HTML, mimetype='text/html')
    return "Plot not generated yet. Please wait and refresh.", 404

@app.route('/stop')
def stop_acquisition():
    """Arresta in sicurezza l'acquisizione dati."""
    global STOP_ACQUISITION
    STOP_ACQUISITION = True
    return "Data acquisition stopped.", 200

# Funzioni per salvataggio ed elaborazione dati
def save_waveforms_to_txt(data, filename):
    """Salva i dati in formato TXT con un nome di evento unico."""
    if data.empty:
        print("WARNING: No data to save to TXT.")
        return

    with open(filename, 'a') as f:  # 'a' per appendere i nuovi dati
        for event, group in data.groupby(level='n_event'):
            # Scrivi l'evento con il suo numero
            f.write(f"# Event {event}\n")
            reordered_group = group[['Time (s)', 'Amplitude (V)']]
            reordered_group.to_csv(f, index=False, header=True, sep='\t')
            f.write("\n")
    print(f"Waveforms saved to TXT file: {filename}")

def save_waveforms_to_root(data, filename):
    """Salva i dati in formato ROOT, separati per evento."""
    if data.empty:
        print("WARNING: No data to save to ROOT.")
        return

    with uproot.recreate(filename) as root_file:
        for event, group in data.groupby('n_event'):  # Usa direttamente 'n_event' come chiave
            tree_data = {
                "Time_s": group["Time (s)"].to_numpy(),
                "Amplitude_V": group["Amplitude (V)"].to_numpy()
            }

            # Salva i dati sotto un evento unico
            root_file[f"Event_{event}"] = tree_data
    print(f"Waveforms saved to ROOT file: {filename}")

def generate_html_plot(data, output_path):
    """Genera un grafico interattivo e lo salva in formato HTML."""
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

# Funzione di acquisizione dati
def data_acquisition_and_processing(digitizer):
    global STOP_ACQUISITION
    n_events = 0
    while not STOP_ACQUISITION:
        try:
            print("Acquiring data from digitizer...")
            with digitizer:
                time.sleep(0.5)
                waveforms = digitizer.get_waveforms()

            if not waveforms:
                print("WARNING: No waveforms acquired. Retrying...")
                continue

            # Converti i dati in DataFrame
            data = convert_dicitonaries_to_data_frame(waveforms)

            # Filtra solo i dati del canale CH0
            ch0_data = data.loc[(slice(None), 'CH0'), :]

            # Applica filtro per il threshold
            ch0_data_above_threshold = ch0_data[ch0_data['Amplitude (V)'] > THRESHOLD]

            if not ch0_data_above_threshold.empty:
                # Salva i dati filtrati in formato TXT e ROOT
                save_waveforms_to_txt(ch0_data_above_threshold, OUTPUT_TXT)
                save_waveforms_to_root(ch0_data_above_threshold, OUTPUT_ROOT)

            # Combina dati del canale CH0 e trigger per il grafico
            trigger_data = data.loc[(slice(None), 'trigger_group_1'), :]
            combined_data = pd.concat([ch0_data_above_threshold, trigger_data])

            # Genera grafico HTML
            generate_html_plot(combined_data, OUTPUT_HTML)

            # Incrementa il contatore eventi
            n_events += len(waveforms)
            print(f"Processed {n_events} events.")

        except Exception as e:
            print(f"Error during acquisition or processing: {e}")

# Main Script
if __name__ == '__main__':
    # Configura il digitizer
    digitizer = CAEN_DT5742_Digitizer(LinkNum=0)
    print('Connected with:', digitizer.idn)
    configure_digitizer(digitizer)

    # Avvia thread per acquisizione dati
    acquisition_thread = threading.Thread(target=data_acquisition_and_processing, args=(digitizer,))
    acquisition_thread.daemon = True
    acquisition_thread.start()

    # Avvia il server Flask
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=8050)