import matplotlib.pyplot as plt
import numpy as np
from rwave import rwaveclient

host = 'localhost'
port = 30001

def main():
    with rwaveclient(host, port, verbose=True) as rwc:
        if rwc is None:
            return

        rwc.send_cmd('sampling 750')
        rwc.send_cmd('grmask 0x1')
        rwc.send_cmd('chmask 0x0003')
        rwc.send_cmd("start")
        rwc.send_cmd('swtrg 1024')
        rwc.send_cmd('readout')
        rwc.send_cmd('download')
        data = rwc.download()
        rwc.send_cmd('stop')

        plot_waveform(data)

def plot_waveform(data):
    """
    Plotta direttamente i dati ricevuti in formato lista di dizionari.
    """
    if not isinstance(data, list) or not data:
        print("Formato dati non valido.")
        return
    
    for i, event in enumerate(data[:5]):  # Plotta i primi 5 eventi
        plt.figure(figsize=(10, 5))
        for ch, waveform in event.items():
            plt.plot(waveform, label=f'Canale {ch}')
        
        plt.xlabel("Campioni")
        plt.ylabel("Ampiezza")
        plt.legend()
        plt.title(f"Evento {i}")
        plt.grid()
        plt.show()

if __name__ == '__main__':
    main()
