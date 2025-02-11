import subprocess
import numpy as np
import uproot
import time
from rwave import rwaveclient

HOST = 'localhost'
PORT = 30001
OUTPUT_FILE = "calibration_data.root"
TREE_NAME = "calibration_tree"
VOLTAGES = np.arange(-0.4, 0.4, 0.01)  # Da -0.4V a 0.4V con step di 0.1V

def configure_pulser_calib(DC_offset):
    """Configuring pulser for calibration loading DC ARB and setting DCOFFS to 0 V."""
    cmd = f"/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'WAVE ARB"
    cmd = f"/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'ARBLOAD DC"
    cmd = f"/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'DCOFFS {DC_offset}'"

def set_pulser_voltage(voltage):
    """Set the pulser DC offset using a bash command."""
    cmd = f"/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'DCOFFS {voltage}'"
    subprocess.run(cmd, shell=True, check=True)
    time.sleep(0.1)  # Wait for voltage to stabilize

def acquire_data():
    """Acquire data from the digitizer."""
    with rwaveclient(HOST, PORT, verbose=True) as rwc:
        if rwc is None:
            return None

        rwc.send_cmd('sampling 750')
        rwc.send_cmd('grmask 0x1')
        rwc.send_cmd('chmask 0x0002')  # Only channel 1 enabled

        rwc.send_cmd("start")
        rwc.send_cmd('swtrg 1024')  
        rwc.send_cmd('readout')
        rwc.send_cmd('download')
        data = rwc.download()
        rwc.send_cmd('stop')
        
        return data

def save_to_root(data_dict, filename):
    """Save collected calibration data to a ROOT file."""
    with uproot.recreate(filename) as file:
        file[TREE_NAME] = data_dict
    print(f"Calibration data saved to {filename}")

if __name__ == "__main__":
    data_dict = {"voltage": [], "event": [], "ch1_waveform": []}
    configure_pulser_calib(0) # prepares pulser at DC = O V
    for v in VOLTAGES:
        set_pulser_voltage(v)
        data = acquire_data()

        if data is None:
            print(f"Failed to acquire data for voltage {v}V")
            continue

        for i, event in enumerate(data):
            data_dict["voltage"].append(v)
            data_dict["event"].append(i)
            data_dict["ch1_waveform"].append(event.get(1, np.zeros(1024)))  # Solo dati del canale 1

    # Convert lists to numpy arrays
    for key in data_dict:
        data_dict[key] = np.array(data_dict[key], dtype=np.float32)

    # Calibrazione: ottieni il massimo valore di ADC per ogni evento (canale 1)
    ch1_max_adc = np.max(data_dict["ch1_waveform"], axis=1)

    # Calibrazione lineare tra ADC e voltaggio
    coeffs = np.polyfit(ch1_max_adc, data_dict["voltage"], 1)  # Fitting lineare
    slope, intercept = coeffs

    print(f"Calibration slope: {slope}, intercept: {intercept}")

    # Aggiungi i parametri di calibrazione al dizionario
    data_dict["slope"] = np.array([slope], dtype=np.float32)
    data_dict["intercept"] = np.array([intercept], dtype=np.float32)

    save_to_root(data_dict, OUTPUT_FILE)
