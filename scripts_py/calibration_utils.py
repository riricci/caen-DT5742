import subprocess
import numpy as np
import uproot
import scipy.stats
import matplotlib.pyplot as plt
import time
from rwave import rwaveclient
from rwaveclient_root import acquire_data

TREE_NAME = "calibration_tree"

# pulser settings 
########################################################

def configure_pulser_calib(DC_offset):
    """Configuring pulser for calibration loading DC ARB and setting DCOFFS to 0 V."""
    cmd = f"/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'WAVE ARB"
    cmd = f"/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'ARBLOAD DC"
    cmd = f"/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'DCOFFS {DC_offset}'"

def set_pulser_voltage(voltage):
    """Set the pulser DC offset using a bash command."""
    # cmd = f"/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-20 --cmd 'DCOFFS {voltage}'"
    cmd = f"/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'DCOFFS {voltage}'"
    subprocess.run(cmd, shell=True, check=True)
    time.sleep(1)  # Wait for voltage to stabilize

# calibration data taking
########################################################
def take_calibration_data(voltages):
    """Acquire calibration data for all voltages."""
    data_dict = {"voltage": [], "event": [], "ch0_waveform": [], "ch1_waveform": []}
    
    for v in voltages:
        set_pulser_voltage(v)
        data = acquire_data()
        
        if data is None:
            print(f"Failed to acquire data for voltage {v}V")
            continue
        
        for i, event in enumerate(data):
            data_dict["voltage"].append(v)
            data_dict["event"].append(i)
            data_dict["ch0_waveform"].append(event.get(0, np.zeros(1024)))
            data_dict["ch1_waveform"].append(event.get(1, np.zeros(1024)))
    
    return data_dict



# data conversion to numpy arrays
########################################################
def convert_calibration_data(data_dict):
    """Convert collected calibration data to numpy arrays."""
    for key in data_dict:
        data_dict[key] = np.array(data_dict[key], dtype=np.float32)
    return data_dict


# ROOT file writing using uproot
########################################################
def save_calibration_to_root(data_dict, filename):
    """Save collected calibration data to a ROOT file."""
    if not data_dict:
        print("No data received!")
        return
    with uproot.recreate(filename) as file:
        file[TREE_NAME] = data_dict
    print(f"Calibration data saved to {filename}")

def load_calib_data_from_root(filename, tree_name="calibration_tree"):
    """Load data from root doing conversion to numpy."""
    with uproot.open(filename) as file:
        tree = file[tree_name]
        voltage_data = tree["voltage"].array(library="np")  # Converte in NumPy direttamente
        ch0_data = tree["ch0_waveform"].array(library="np")
        ch1_data = tree["ch1_waveform"].array(library="np")
    return voltage_data, ch0_data, ch1_data

# p0 and p1 calibration parameters extraction and writing to ROOT file
########################################################
def calc_calibration_parameters(voltage_data, ch_waveform):
    """Performs calibration for each one of the 1024 cells."""
    num_cells = ch_waveform.shape[1]  # Dovrebbe essere 1024
    calibration_params = []
    
    for cell in range(num_cells):
        adc_values = ch_waveform[:, cell]  # ADC per la cella specifica
        slope, intercept, _, _, _ = scipy.stats.linregress(voltage_data, adc_values)
        calibration_params.append((slope, intercept))
    
    return np.array(calibration_params)  # Restituisce una lista di (slope, intercept) per cella

    
# plotting calibration curves for the first 4 cells for ch1
########################################################
def plot_calibration_ch1(voltage_data, ch1_waveform, calibration_params, num_cells_to_plot=4):
    """Plots calibration for the first 4 cells for ch1."""
    plt.figure(figsize=(10, 6))
    for cell in range(num_cells_to_plot):
        adc_values = ch1_waveform[:, cell]
        slope, intercept = calibration_params[cell]
        
        plt.scatter(voltage_data, adc_values, label=f'Cell {cell} Data')
        plt.plot(voltage_data, slope * voltage_data + intercept, label=f'Cell {cell} Fit')
    
    plt.xlabel('Voltage (V)')
    plt.ylabel('ADC Value')
    plt.title('Calibration for first 4 cells (ch1)')
    plt.legend()
    plt.show()
