import sys
import numpy as np
from rwave import rwaveclient
import uproot

HOST = 'localhost'
PORT = 30001

OUTPUT_FILE = "output.root"
TREE_NAME = "waveform_tree"

def acquire_data():
    with rwaveclient(HOST, PORT, verbose=True) as rwc:
        if rwc is None:
            return None

        # Configura il digitizer
        rwc.send_cmd('sampling 750')
        rwc.send_cmd('grmask 0x1')
        rwc.send_cmd('chmask 0x0003')

        # Avvia l'acquisizione
        rwc.send_cmd("start")

        # Acquisisci i dati
        rwc.send_cmd('swtrg 1024')  # Trigger software
        rwc.send_cmd('readout')
        rwc.send_cmd('download')
        data = rwc.download()
        
        # Ferma l'acquisizione
        rwc.send_cmd('stop')
        
        return data

def save_to_root(data, filename):
    if data is None:
        print("No data received!")
        return

    events = []
    ch0_data = []
    ch1_data = []

    # Processa i dati
    for i, event in enumerate(data):
        events.append(i)  # Numero evento
        ch0_data.append(event.get(0, np.zeros(1024)))  # Se ch0 non esiste, usa zeri
        ch1_data.append(event.get(1, np.zeros(1024)))  # Se ch1 non esiste, usa zeri

    # Converti in array numpy
    events = np.array(events, dtype=np.int32)
    ch0_data = np.array(ch0_data, dtype=np.float32)
    ch1_data = np.array(ch1_data, dtype=np.float32)

    # Scrive su file ROOT
    with uproot.recreate(filename) as file:
        file[TREE_NAME] = {
            "event": events,
            "ch0_waveform": ch0_data,
            "ch1_waveform": ch1_data
        }
    print(f"Dati salvati in {filename}")

if __name__ == "__main__":
    data = acquire_data()
    save_to_root(data, OUTPUT_FILE)
