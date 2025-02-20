# 2025.02.10 Riccardo Ricci
# TO BE UPDATED after having the final version of the calibration_utils.py

import sys
import numpy as np
sys.path.append("/eu/caen-dt5742b/python/")
from rwave import rwaveclient
import uproot
import matplotlib.pyplot as plt

HOST = 'localhost'
PORT = 30001

OUTPUT_FILE = "output.root"
TREE_NAME = "waveform_tree"


def acquire_data():
    """Acquires waveform data from the digitizer."""
    with rwaveclient(HOST, PORT, verbose=True) as rwc:
        if rwc is None:
            return None

        rwc.send_cmd('sampling 750')
        rwc.send_cmd('grmask 0x1')
        rwc.send_cmd('chmask 0x0003')
        rwc.send_cmd("start")
        rwc.send_cmd('swtrg 1024')
        rwc.send_cmd('readout')
        rwc.send_cmd('download')
        data = rwc.download()
        rwc.send_cmd('stop')
        
        return data

def save_waveforms_to_root(data, filename):
    """Saves processed waveform data into a ROOT file."""
    if data is None:
        print("No data received!")
        return
    
    # Dictionary to store data in the correct format for uproot
    tree_data = {"waveform_ch0": [], "waveform_ch1": [], "trigger_tag": [], "first_cell": []}

    for event in data:
        tree_data["waveform_ch0"].append(event[0]["waveform"])
        tree_data["waveform_ch1"].append(event[1]["waveform"])
        tree_data["trigger_tag"].append(event[0]["trigger_tag"])  # Store the trigger value directly
        tree_data["first_cell"].append(event[0]["first_cell"])  # Store the first cell value directly

    # Convert lists to NumPy arrays
    tree_data = {key: np.array(value) for key, value in tree_data.items()}

    # Write to ROOT file
    with uproot.recreate(filename) as file:
        file[TREE_NAME] = tree_data



def plot_waveform(data):
    """Plots waveform data for a given event."""
    plt.figure(figsize=(10, 6))
    
    plt.plot(data[0][0]["waveform"], label=f"Channel 0", color='blue')
    plt.plot(data[0][1]["waveform"], label=f"Channel 1", color='red')

    
    plt.xlabel('Sample')
    plt.ylabel('Amplitude')
    plt.title(f'Waveform for Event a caso')
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    data = acquire_data()
    # plot_waveform(data)
    save_waveforms_to_root(data, OUTPUT_FILE)
    
