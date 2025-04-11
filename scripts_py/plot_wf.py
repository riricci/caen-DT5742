import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt

# Look for the most recent .npz file in the ./data directory
def find_latest_npz_file(data_dir="./data"):
    files = [f for f in os.listdir(data_dir) if f.endswith(".npz")]
    if not files:
        raise FileNotFoundError("No .npz files found in ./data")
    files.sort(reverse=True)
    return os.path.join(data_dir, files[0])

# Load waveform data from a .npz file
def load_waveforms(npz_path):
    data = np.load(npz_path)
    return data

# Convert ADC counts to millivolts (assuming 12-bit ADC centered at 2048)
def adc_to_mv(adc_array):
    return ((adc_array - 2048) / 4096.0) * 1000  # mV

# Apply low-pass Butterworth filter to reduce noise
def lowpass_filter(wf, cutoff_hz=200e6, fs=5e9, order=4):
    nyq = fs / 2.0
    normal_cutoff = cutoff_hz / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    filtered = filtfilt(b, a, wf)
    return filtered

# Calculate baseline using a region while excluding potential signal contamination
def calculate_baseline_with_mask(wf, baseline_start, baseline_end, window_size=20, ptp_threshold=5.0, pre_margin=30, post_margin=150):
    region = wf[baseline_start:baseline_end]
    num_points = len(region)
    region_indices = np.arange(baseline_start, baseline_end)

    # Compute peak-to-peak value over sliding windows
    ptp = np.array([
        np.ptp(region[i:i+window_size])
        for i in range(num_points - window_size)
    ])
    # Detect regions likely containing signal
    peak_indices = np.where(ptp > ptp_threshold)[0] + baseline_start

    # Create mask to exclude signal + margins
    exclude_mask = np.zeros_like(wf, dtype=bool)
    for idx in peak_indices:
        start = max(0, idx - pre_margin)
        end = min(len(wf), idx + post_margin)
        exclude_mask[start:end] = True

    # Keep only valid indices for baseline calculation
    usable_indices = region_indices[~exclude_mask[baseline_start:baseline_end]]

    if len(usable_indices) > 0:
        baseline = np.median(wf[usable_indices])
    else:
        baseline = np.median(region)
        usable_indices = np.array([])

    print(f"✅ {len(usable_indices)} samples used for baseline after excluding signal + margins")
    return baseline, usable_indices

# Helper to group consecutive indices (for plotting spans)
def group_consecutive(indices):
    if len(indices) == 0:
        return []
    groups = []
    start = indices[0]
    for i in range(1, len(indices)):
        if indices[i] != indices[i-1] + 1:
            groups.append((start, indices[i-1]))
            start = indices[i]
    groups.append((start, indices[-1]))
    return groups

# Main plotting function: shows first waveform per channel
def plot_first_waveform(data, unit='ADC'):
    baseline_start, baseline_end = 49, 973

    for key in data.files:
        wf_array = data[key]
        if wf_array.ndim == 2 and wf_array.shape[0] > 0:
            wf_adc = wf_array[0]
            if unit == 'mV':
                wf = adc_to_mv(wf_adc)
                baseline, baseline_indices = calculate_baseline_with_mask(wf, baseline_start, baseline_end)
                wf -= baseline

                # Apply filter
                wf_filt = lowpass_filter(wf)

                # Plot comparison: raw vs filtered
                plot_filtered_vs_raw(wf, wf_filt, title=f"{key}: raw vs filtered")
                wf = wf_filt  # Optionally replace with filtered for further plotting

            else:
                wf = wf_adc
                baseline_indices = []

            plt.plot(wf, label=key)

            if unit == 'mV':
                # Full candidate window
                plt.axvspan(baseline_start, baseline_end, color='orange', alpha=0.2, label='Candidate window')
                # Actual baseline points used
                grouped = group_consecutive(baseline_indices)
                for start, end in grouped:
                    plt.axvspan(start, end + 1, color='green', alpha=0.2, label='Used for baseline')

        else:
            print(f"⚠️ Skipping {key}: not a 2D waveform array.")

    plt.title(f"First waveform per channel ({unit})")
    plt.xlabel("Sample index")
    plt.ylabel(f"Amplitude [{unit}]")
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))  # remove duplicates
    plt.legend(by_label.values(), by_label.keys())
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# Show raw vs filtered waveform to see the effect of noise filtering
def plot_filtered_vs_raw(wf, filtered_wf, title="Low-pass filter effect"):
    plt.figure(figsize=(10, 4))
    plt.plot(wf, label="Raw", alpha=0.6)
    plt.plot(filtered_wf, label="Filtered (200 MHz)", linewidth=1.5)
    plt.xlabel("Sample index")
    plt.ylabel("Amplitude [mV]")
    plt.title(title)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

# Command line interface to select file and units
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot waveforms from a saved .npz file.")
    parser.add_argument("--file", type=str, help="Name of the .npz file to load from ./data/")
    parser.add_argument("--unit", choices=["ADC", "mV"], default="ADC", help="Unit for waveform plot.")
    args = parser.parse_args()

    if args.file:
        npz_path = os.path.join("./data", args.file)
        if not os.path.isfile(npz_path):
            raise FileNotFoundError(f"Specified file not found: {npz_path}")
    else:
        npz_path = find_latest_npz_file()

    print(f"📂 Loading waveforms from: {npz_path}")
    wf_data = load_waveforms(npz_path)
    plot_first_waveform(wf_data, unit=args.unit)
