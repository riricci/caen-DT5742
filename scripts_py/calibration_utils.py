import subprocess
import numpy as np
import uproot
import scipy.stats
import matplotlib.pyplot as plt
import time
from rwave import rwaveclient
from rwaveclient_root import acquire_data
import argparse

HOST = 'localhost'
PORT = 30001
OUTPUT_FILE = "calibration_data.root"
TREE_NAME = "calibration_tree"
VOLTAGES = np.arange(-0.4, 0.4, 0.15)  # Voltage range from -0.4V to 0.4V


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

def set_pulser_voltage(voltage, sleep):
    """Sets the pulser DC offset."""
    cmd = f"/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'DCOFFS {voltage}'"
    subprocess.run(cmd, shell=True, check=True)
    time.sleep(sleep)  # Allow voltage stabilization


# data conversion to numpy arrays
########################################################
def convert_calibration_data(data_dict):
    """Convert collected calibration data to numpy arrays."""
    for key in data_dict:
        data_dict[key] = np.array(data_dict[key], dtype=np.float32)
    return data_dict

# ROOT file writing using uproot for any dictionary
########################################################
def save_to_root(data_dict, filename):
    """Saves the collected [calibration] data to a ROOT file."""
    with uproot.recreate(filename) as file:
        file[TREE_NAME] = data_dict
    print(f"Calibration data saved to {filename}")

# to be checked/updated - not used for now
# def load_calib_data_from_root(filename, tree_name="calibration_tree"):
#     """Load data from root doing conversion to numpy."""
#     with uproot.open(filename) as file:
#         tree = file[tree_name]
#         voltage_data = tree["voltage"].array(library="np")  # Converte in NumPy direttamente
#         ch0_data = tree["ch0_waveform"].array(library="np")
#         ch1_data = tree["ch1_waveform"].array(library="np")
#     return voltage_data, ch0_data, ch1_data

# p0 and p1 calibration parameters extraction and writing to ROOT file
# TO BE CHECKED/UPDATED
########################################################
# def calc_calibration_parameters(voltage_data, ch_waveform):
#     """Performs calibration for each one of the 1024 cells."""
#     num_cells = ch_waveform.shape[1]  # Dovrebbe essere 1024
#     calibration_params = []
    
#     for cell in range(num_cells):
#         adc_values = ch_waveform[:, cell]  # ADC per la cella specifica
#         slope, intercept, _, _, _ = scipy.stats.linregress(voltage_data, adc_values)
#         calibration_params.append((slope, intercept))
    
#     return np.array(calibration_params)  # Restituisce una lista di (slope, intercept) per cella


# calibration data taking
########################################################
def take_calibration_data():
    """Acquire calibration data using argparse to set parameters dynamically."""
    parser = argparse.ArgumentParser(
        description="Calibration data acquisition.",
        usage="python calibration_script.py --vmin MIN --vmax MAX --step STEP --output_file filename.root"
    )
    parser.add_argument(
        "--vmin", type=float, default=-0.4,
        help="Minimum voltage for calibration (default: -0.4V)."
    )
    parser.add_argument(
        "--vmax", type=float, default=0.4,
        help="Maximum voltage for calibration (default: 0.4V)."
    )
    parser.add_argument(
        "--step", type=float, default=0.15,
        help="Step size for voltage increments (default: 0.15V)."
    )
    parser.add_argument(
        "--sleep", type=float, default=0.1,
        help="Sleep time for voltage stabilization (default: 1s)."
    )
    parser.add_argument(
        "--output_file", type=str, default="calibration_data.root",
        help="Output ROOT file to store calibration data (default: calibration_data.root)."
    )
    args = parser.parse_args()

    voltages = np.arange(args.vmin, args.vmax + args.step, args.step)
    s = args.sleep 
    output_file = args.output_file

    data_dict = {"voltage": [], "event": [], "ch1_waveform": []}

    configure_pulser_calib()
    for v in voltages:
        set_pulser_voltage(v,s)
        all_ch1_waveforms = []
        data = acquire_data()
        
        if data is None:
            print(f"Failed to acquire data for voltage {v}V")
            continue

        for i, event in enumerate(data):
            ch1_waveform = event.get(1, np.zeros(1024))  # Channel 1
            all_ch1_waveforms.append(ch1_waveform)   

        mean_ch1_waveform = np.mean(all_ch1_waveforms, axis=0)
        data_dict["voltage"].append(v)
        data_dict["event"].append(0)  
        data_dict["ch1_waveform"].append(mean_ch1_waveform)

    data_dict = convert_calibration_data(data_dict)
    save_to_root(data_dict, output_file)
    plot_adc_vs_voltage(data_dict["voltage"], data_dict["ch1_waveform"])

    # back to DC=0 V for other uses
    set_pulser_voltage(0, s)

    
# plotting calibration curves for the first 4 cells for ch1
########################################################
# used only as control plot for now - used at the end of data taking

def plot_adc_vs_voltage(voltage_data, ch1_waveform):
    """Plots ADC vs Voltage for the first cell, including fit parameters and chi² in the legend."""
    adc_values = ch1_waveform[:, 0]  # First cell only
    # fit
    slope, intercept, _, _, _ = scipy.stats.linregress(voltage_data, adc_values)
    fitted_values = slope * voltage_data + intercept
    # chi2/ndof (manually done, not from scipy.stats.linregress!!)
    residuals = adc_values - fitted_values
    chi2 = np.sum((residuals ** 2) / fitted_values)  # Standard definition of chi²
    ndof = len(voltage_data) - 2  # Degrees of freedom (N data points - 2 fit parameters)
    chi2_reduced = chi2 / ndof if ndof > 0 else np.nan  # Avoid division by zero
    
    # Plot 
    plt.scatter(voltage_data, adc_values, label='Cell 0 Data', c='black', s=10)
    # Fit
    plt.plot(voltage_data, fitted_values, label=f'Fit: y = {slope:.2f}x + {intercept:.2f}\n$\\chi^2_{{red}}$ = {chi2_reduced:.2f}', 
             c='red', linewidth=0.8)
    # labelsssss
    plt.xlabel('Voltage (V)')
    plt.ylabel('ADC Value')
    plt.title('ADC vs Voltage for Cell 0')
    plt.legend()
    plt.show()


