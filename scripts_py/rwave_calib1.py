import subprocess
import numpy as np
import uproot
import time
import matplotlib.pyplot as plt
from rwave import rwaveclient

HOST = 'localhost'
PORT = 30001
OUTPUT_FILE = "calibration_data.root"
TREE_NAME = "calibration_tree"
VOLTAGES = np.arange(-0.4, 0.4, 0.15)  # Voltage range from -0.4V to 0.4V

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

def acquire_data():
    """Acquires data from the digitizer."""
    with rwaveclient(HOST, PORT, verbose=True) as rwc:
        if rwc is None:
            return None
        
        rwc.send_cmd('sampling 750')
        rwc.send_cmd('grmask 0x1')
        rwc.send_cmd('chmask 0x0002')  # Enable only channel 1
        
        rwc.send_cmd("start")
        rwc.send_cmd('swtrg 1')  # Software trigger
        rwc.send_cmd('readout')
        rwc.send_cmd('download')
        data = rwc.download()
        rwc.send_cmd('stop')
        
        return data

def save_to_root(data_dict, filename):
    """Saves the collected calibration data to a ROOT file."""
    with uproot.recreate(filename) as file:
        file[TREE_NAME] = data_dict
    print(f"Calibration data saved to {filename}")

def plot_adc_vs_voltage(voltage_data, ch1_waveform):
    """Plots ADC vs Voltage for the first cell."""
    adc_values = ch1_waveform[:, 0]  # First cell only
    
    plt.scatter(voltage_data, adc_values, label='Cell 0 Data', c='black', s=2)
    plt.xlabel('Voltage (V)')
    plt.ylabel('ADC Value')
    plt.title('ADC vs Voltage for Cell 0')
    plt.legend()
    plt.show()

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
