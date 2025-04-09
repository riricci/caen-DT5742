import sys
import numpy as np
import argparse
import matplotlib.pyplot as plt
import uproot
from tqdm import tqdm  # Barra di avanzamento
from datetime import datetime
import os

sys.path.append("/eu/caen-dt5742b/python/")
from rwave import rwaveclient

parser = argparse.ArgumentParser(description="Receive and save waveform data from CAEN digitizer.")
parser.add_argument("--filter_ADC", type=float, default=None,
                    help="Apply filter on central peak-to-peak amplitude (ADC units).")
parser.add_argument("--channel", type=int, nargs='+', default=None, 
                    help="Specify channel(s) to acquire data from (e.g., --channel 1 3 4).")
parser.add_argument("--min_events", type=int, default=1000, 
                    help="Minimum number of valid waveforms to accumulate before saving.")
parser.add_argument("--log_file", type=str, default="acquisition_log.txt", 
                    help="Log file to record acquisition details.")
args = parser.parse_args()


# Create data directory if it doesn't exist
os.makedirs("./data", exist_ok=True)

HOST = 'localhost'
PORT = 30001

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = f"./data/{timestamp}_waveforms.root"
NPZ_FILE = f"./data/{timestamp}_waveforms.npz"
TREE_NAME = "waveform_tree"



def acquire_data(chmask, correction):
    """Acquire waveform data from the digitizer."""
    with rwaveclient(HOST, PORT, verbose=True) as rwc:
        if rwc is None:
            return None

        rwc.send_cmd('sampling 5000')
        rwc.send_cmd('grmask 0x1')
        rwc.send_cmd(f'chmask {chmask}')
        rwc.send_cmd('correction on' if correction else 'correction off')
        rwc.send_cmd("start")
        rwc.send_cmd('swtrg 1024')
        rwc.send_cmd('readout')
        rwc.send_cmd('download')
        data = rwc.download()
        rwc.send_cmd('stop')

        return data


def handle_data(data, selected_ch=None):
    """Process waveform data and return one dictionary per event."""
    if data is None:
        print("No data received.")
        return None

    all_events_data = []
    max_channels = len(data[0])

    if selected_ch is not None:
        active_channels = selected_ch
    else:
        active_channels = range(max_channels)

    for event_number, event in enumerate(data):
        for ch in active_channels:
            waveform = event[ch]["waveform"]
            tree_data = {
                "event_number": np.array([event_number]),
                f'waveform_ch{ch}': np.array([waveform]),
                "trigger_tag": np.array([event[0]["trigger_tag"]]),
                "first_cell": np.array([event[0]["first_cell"]]),
                "num_cells": np.array([np.arange(len(waveform))])
            }
            all_events_data.append(tree_data)

    return all_events_data


def apply_filter(event_data, threshold=20, window_size=900):
    """Filter waveform events based on central peak-to-peak amplitude."""
    start_idx = (1024 - window_size) // 2
    end_idx = start_idx + window_size
    filtered_dict = {}

    for event in event_data:
        for key in event:
            if key.startswith("waveform_ch"):
                ch = key.split("waveform_ch")[1]
                wf = event[key].squeeze()
                central_window = wf[start_idx:end_idx]
                peak_to_peak = central_window.max() - central_window.min()
                if peak_to_peak > threshold:
                    if f'waveform_ch{ch}' not in filtered_dict:
                        filtered_dict[f'waveform_ch{ch}'] = []
                    filtered_dict[f'waveform_ch{ch}'].append(wf)

    return filtered_dict


def save_filtered_waveforms_to_npz(filtered_dict, output_file):
    """Save filtered waveforms to compressed .npz file."""
    if filtered_dict:
        for ch_key, wfs in filtered_dict.items():
            print(f"{ch_key}: {len(wfs)} waveforms passed the filter.")
        np.savez_compressed(output_file, **{k: np.array(v) for k, v in filtered_dict.items()})
        print(f"Filtered NPZ file saved as: {output_file}")
    else:
        print("⚠️ No waveform passed the filter.")
    return bool(filtered_dict)


def save_waveforms_to_root(filtered_dict, output_file):
    """Save filtered waveforms into separate ROOT files per channel."""
    for ch_key, waveforms in filtered_dict.items():
        ch = ch_key.replace("waveform_ch", "")
        with uproot.recreate(f'ch{ch}_{output_file}') as file:
            for i, wf in enumerate(waveforms):
                file[f"{TREE_NAME}_event_{i}"] = {
                    "event_number": np.array([i]),
                    f"waveform_ch{ch}": np.array([wf]),
                    "trigger_tag": np.array([0]),
                    "first_cell": np.array([0]),
                    "num_cells": np.array([np.arange(len(wf))])
                }
        print(f"ROOT file saved: ch{ch}_{output_file}")


if __name__ == "__main__":
    selected_channels = args.channel if args.channel else None
    print(f"Selected channels: {selected_channels}")

    min_events = args.min_events
    print(f"Accumulating at least {min_events} valid waveforms.")

    # Initialize list to store valid waveforms
    valid_waveforms = []
    run_count = 0

    # Open log file
    with open(args.log_file, 'w') as log_file:
        log_file.write(f"Acquisition started. Accumulating at least {min_events} waveforms.\n")
        log_file.write(f"Selected channels: {selected_channels}\n")

        # Barra di avanzamento
        pbar = tqdm(total=min_events, desc="Accumulating waveforms", ncols=100, unit="waveforms")

        while len(valid_waveforms) < min_events:
            run_count += 1
            print(f"\nRun {run_count}: Accumulating waveforms... ({len(valid_waveforms)} / {min_events})")
            data = acquire_data(0x0003, correction=True)
            if data is None:
                sys.exit("❌ Acquisition failed.")

            event_data = handle_data(data, selected_ch=selected_channels)
            if event_data is None:
                sys.exit("❌ No events to process.")

            if args.filter_ADC is not None:
                print(f"🔍 Applying filter: peak-to-peak > {args.filter_ADC} ADC")
                filtered = apply_filter(event_data, threshold=args.filter_ADC)

                # Append valid waveforms to the list
                for ch_key, waveforms in filtered.items():
                    valid_waveforms.extend(waveforms)

                print(f"Waveforms after filtering: {len(valid_waveforms)}")
            else:
                print("No filter applied. Saving all waveforms.")
                for event in event_data:
                    for ch_key in event:
                        if ch_key.startswith("waveform_ch"):
                            valid_waveforms.append(event[ch_key])

            # Update barra di avanzamento
            pbar.update(len(valid_waveforms) - pbar.n)

            # Scrivi nel log
            log_file.write(f"Run {run_count}: {len(valid_waveforms)} valid waveforms accumulated\n")
        
        # Fine del ciclo
        print(f"\n{len(valid_waveforms)} valid waveforms accumulated. Saving to NPZ and ROOT.")
        np.savez_compressed(NPZ_FILE, waveforms=np.array(valid_waveforms))
        # save_waveforms_to_root({"waveform_ch": valid_waveforms}, OUTPUT_FILE)

        # Aggiorna il log finale
        log_file.write(f"Acquisition complete. {len(valid_waveforms)} valid waveforms saved.\n")
        pbar.close()

    print("Waveforms saved.")
