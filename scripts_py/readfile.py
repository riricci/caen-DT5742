import uproot
import matplotlib.pyplot as plt

# Funzione per caricare i dati da un file ROOT
def load_data_from_root(filename):
    # Apre il file ROOT
    with uproot.open(filename) as file:
        # Carica il TTree
        tree = file["waveform_tree"]
        
        # Estrai i dati per ogni canale (ch0, ch1) e gli eventi
        events = tree["event"].array()
        ch0_data = tree["ch0_waveform"].array()
        ch1_data = tree["ch1_waveform"].array()
        
    return events, ch0_data, ch1_data

# Funzione per plottare le waveforms
def plot_waveform(ch0_data, ch1_data, event_index=0):
    # Seleziona i dati per l'evento specificato (default è il primo evento)
    ch0 = ch0_data[event_index]
    ch1 = ch1_data[event_index]

    # Plot delle waveforms per i due canali
    plt.figure(figsize=(10, 6))
    plt.plot(ch0, label="Channel 0", color='blue')
    plt.plot(ch1, label="Channel 1", color='red')
    plt.xlabel('Sample')
    plt.ylabel('Amplitude')
    plt.title(f'Waveform for Event {event_index}')
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    # Carica i dati dal file ROOT
    filename = "output.root"
    events, ch0_data, ch1_data = load_data_from_root(filename)
    
    # Plotta la waveform del primo evento
    plot_waveform(ch0_data, ch1_data, event_index=0)
