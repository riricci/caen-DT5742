import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
from tkinter import ttk
from rwave import rwaveclient

host = 'localhost'
port = 30001

class WaveformApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Waveform Viewer")
        
        self.sampling_freq = 750  # Default frequency
        self.running = False
        
        self.create_widgets()
    
    def create_widgets(self):
        control_frame = ttk.Frame(self.root)
        control_frame.pack(side=tk.TOP, fill=tk.X)
        
        self.freq_label = ttk.Label(control_frame, text=f"Sampling Frequency: {self.sampling_freq} MHz")
        self.freq_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        for freq in [750, 1000, 2500, 5000]:
            btn = ttk.Button(control_frame, text=str(freq), command=lambda f=freq: self.set_frequency(f))
            btn.pack(side=tk.LEFT, padx=2)
        
        self.trigger_btn = ttk.Button(control_frame, text="Send Trigger", command=self.send_trigger)
        self.trigger_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.canvas_frame = ttk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.fig, self.ax = plt.subplots()
        self.canvas = None
        self.update_plot([])
    
    def set_frequency(self, freq):
        if not self.running:
            self.sampling_freq = freq
            self.freq_label.config(text=f"Sampling Frequency: {self.sampling_freq} MHz")
    
    def send_trigger(self):
        if self.running:
            return
        
        self.running = True
        with rwaveclient(host, port, verbose=True) as rwc:
            if rwc is None:
                self.running = False
                return
            
            rwc.send_cmd(f'sampling {self.sampling_freq}')
            rwc.send_cmd('grmask 0x1')
            rwc.send_cmd('chmask 0x0003')
            rwc.send_cmd('start')
            rwc.send_cmd('swtrg 1024')
            rwc.send_cmd('readout')
            rwc.send_cmd('download')
            data = rwc.download()
            rwc.send_cmd('stop')
            
        self.update_plot(data)
        self.running = False
    
    def update_plot(self, data):
        self.ax.clear()
        
        if data:
            for event in data:
                for channel, waveform in event.items():
                    self.ax.plot(waveform, label=f'Ch {channel}')
        
        self.ax.set_xlabel("Sample")
        self.ax.set_ylabel("Amplitude")
        self.ax.set_title("Waveform Data")
        self.ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1))
        
        if self.canvas:
            self.canvas.get_tk_widget().pack_forget()
        
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = WaveformApp(root)
    root.mainloop()
