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
def configure_pulser_calib():
    """Configures pulser for calibration by setting ARB mode and initializing DC offset."""
    cmds = [
        "/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'WAVE ARB'",
        "/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'ARBLOAD DC'",
        "/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'DCOFFS 0'"
    ]
    for cmd in cmds:
        subprocess.run(cmd, shell=True, check=True)
    time.sleep(0.1)

def set_pulser_voltage(voltage):
    """Sets the pulser DC offset."""
    cmd = f"/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'DCOFFS {voltage}'"
    subprocess.run(cmd, shell=True, check=True)
    time.sleep(0.1)  # Allow voltage stabilization

# data taking
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
def save_to_root(data_dict, filename):
    """Saves the collected [calibration] data to a ROOT file."""
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
def plot_adc_vs_voltage(voltage_data, ch1_waveform):
    """Plots ADC vs Voltage for the first cell."""
    adc_values = ch1_waveform[:, 0]  # First cell only
    
    plt.scatter(voltage_data, adc_values, label='Cell 0 Data', c='black', s=2)
    # do fit and estimate regression parameters
    slope, intercept, _, _, _ = scipy.stats.linregress(voltage_data, adc_values)
    # plot the fit
    plt.plot(voltage_data, slope*voltage_data + intercept, label=f'Cell 0 Fit (slope={slope:.2f}, intercept={intercept:.2f})', c='red')
    plt.xlabel('Voltage (V)')
    plt.ylabel('ADC Value')
    plt.title('ADC vs Voltage for Cell 0')
    plt.legend()
    plt.show()

