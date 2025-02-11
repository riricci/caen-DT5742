import subprocess
import numpy as np
import uproot
import time
import matplotlib.pyplot as plt
from rwave import rwaveclient
from rwaveclient_root import acquire_data
from calibration_utils import configure_pulser_calib, set_pulser_voltage, save_to_root, plot_adc_vs_voltage

HOST = 'localhost'
PORT = 30001
OUTPUT_FILE = "calibration_data.root"
TREE_NAME = "calibration_tree"
VOLTAGES = np.arange(-0.4, 0.4, 0.15)  # Voltage range from -0.4V to 0.4V


if __name__ == "__main__":
    data_dict = {"voltage": [], "event": [], "ch1_waveform": []}
    
    configure_pulser_calib()
    for v in VOLTAGES:
        set_pulser_voltage(v)
        data = acquire_data()
        
        if data is None:
            print(f"Failed to acquire data for voltage {v}V")
            continue
        
        for i, event in enumerate(data):
            data_dict["voltage"].append(v)
            data_dict["event"].append(i)
            data_dict["ch1_waveform"].append(event.get(1, np.zeros(1024)))
    
    # Convert lists to numpy arrays
    for key in data_dict:
        data_dict[key] = np.array(data_dict[key], dtype=np.float32)
    
    save_to_root(data_dict, OUTPUT_FILE)
    
    # Generate control plot
    plot_adc_vs_voltage(data_dict["voltage"], data_dict["ch1_waveform"])
