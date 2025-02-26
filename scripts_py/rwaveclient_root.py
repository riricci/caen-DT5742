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

OUTPUT_FILE = "waveforms.root"
TREE_NAME = "waveform_tree"


def acquire_data(chmask):
    """Acquires waveform data from the digitizer."""
    with rwaveclient(HOST, PORT, verbose=True) as rwc:
        if rwc is None:
            return None

        rwc.send_cmd('sampling 750')
        rwc.send_cmd('grmask 0x1')
        rwc.send_cmd(f'chmask {chmask}')
        rwc.send_cmd("start")
        rwc.send_cmd('swtrg 1024')
        rwc.send_cmd('readout')
        rwc.send_cmd('download')
        data = rwc.download()
        rwc.send_cmd('stop')
        
        return data



def handle_data(data, selected_ch=None):
    """Processes waveform data, returning one tree per event."""
    if data is None:
        print("No data received!")
        return

    all_events_data = []  # List to store each event as a separate tree
    max_channels = len(data[0])  # Number of active channels

    # Determine which channels to process
    if selected_ch is not None:
        if selected_ch < 0 or selected_ch >= max_channels:
            print(f"Channel {selected_ch} is not available. Active channels: 0 to {max_channels - 1}.")
            return
        active_channels = [selected_ch]
    else:
        active_channels = range(max_channels)

    # Loop over each event
    for event_number, event in enumerate(data):
        for ch in active_channels:
            waveform = event[ch]["waveform"]
            tree_data = {
                "event_number": np.array([event_number]),
                f'waveform_ch{ch}': np.array([waveform]),
                "trigger_tag": np.array([event[0]["trigger_tag"]]),
                "first_cell": np.array([event[0]["first_cell"]]),
                "num_cells": np.array([np.arange(len(waveform))])  # Array from 0 to 1023
            }
            all_events_data.append(tree_data)

    return all_events_data


# save to root possibly everything
def save_waveforms_to_root(data, output_file):
    """Saves waveform data into one ROOT file per channel, with separate events."""
    event_data = handle_data(data)
    
    if event_data is None:
        print("No data to save.")
        return

    # Save each channel's data in a separate ROOT file
    for ch in range(len(data[0])):
        with uproot.recreate(f'ch{ch}_{output_file}') as file:
            for i, event in enumerate(event_data):
                if f'waveform_ch{ch}' in event:
                    file[f"{TREE_NAME}_event_{i}"] = event




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
    data = acquire_data(0x0003)
    # plot_waveform(data)
    save_waveforms_to_root(data, OUTPUT_FILE)
    # print(handle_data(data))
    
