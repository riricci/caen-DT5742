import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget, QVBoxLayout, QPushButton, QLabel, QFrame
import pyqtgraph as pg
from rwave import rwaveclient
import threading

host = 'localhost'
port = 30001

class OscilloscopeApp(QWidget):
    def __init__(self):
        super().__init__()
        self.host = 'localhost'
        self.port = 30001
        self.current_frequency = 750
        self.channel_visibility = {0: True, 1: True}  # Track visibility of channels
        self.latest_data = None
        self.initUI()
        pg.setConfigOptions(antialias=False, useOpenGL=True)  # Disable antialiasing and enable OpenGL for performance
        
    def set_frequency(self, freq):
        self.current_frequency = freq
        threading.Thread(target=self.configure_digitizer, daemon=True).start()

    def configure_digitizer(self):
        with rwaveclient(self.host, self.port, verbose=True) as rwc:
            if rwc is not None:
                rwc.send_cmd(f'sampling {self.current_frequency}')
                print(f"Configured digitizer to {self.current_frequency} MHz")    
                rwc.send_cmd('grmask 0x1')
                rwc.send_cmd('chmask 0x0003')

    def toggle_channel(self, ch):
        self.channel_visibility[ch] = not self.channel_visibility[ch]
        if self.latest_data:
            self.plotData(self.latest_data)
    
    def initUI(self):
        layout = QVBoxLayout()
        self.setWindowTitle("Digitizer Control")
        self.setGeometry(100, 100, 900, 600)
        
        # Graph widget
        self.plotWidget = pg.PlotWidget()
        self.plotWidget.setBackground('black')
        self.plotWidget.showGrid(x=True, y=True)
        
        # Configure axes
        self.plotWidget.setLabel('left', 'Amplitude')
        self.plotWidget.setLabel('bottom', 'Samples')
        
        layout.addWidget(self.plotWidget)
        
        # Button layout
        control_layout = QHBoxLayout()
        
        self.button = QPushButton('Start Acquisition')
        self.button.clicked.connect(self.startAcquisition)
        control_layout.addWidget(self.button)
        
        self.freq_buttons = []
        for freq in [750, 1000, 2500, 5000]:  # Frequencies in MHz
            btn = QPushButton(f"{freq} MHz", self)
            btn.clicked.connect(lambda _, f=freq: self.set_frequency(f))
            self.freq_buttons.append(btn)
            control_layout.addWidget(btn)
        
        layout.addLayout(control_layout)
        
        # Channel toggle buttons
        self.channel_buttons = {}
        ch_layout = QHBoxLayout()
        for ch in [0, 1]:
            btn = QPushButton(f"Toggle Ch {ch}", self)
            btn.clicked.connect(lambda _, c=ch: self.toggle_channel(c))
            self.channel_buttons[ch] = btn
            ch_layout.addWidget(btn)
        
        layout.addLayout(ch_layout)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Status label
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def startAcquisition(self):
        self.button.setEnabled(False)
        self.status_label.setText("Status: Acquiring Data...")
        data = self.acquireData()
        if data:
            self.plotData(data)
        self.button.setEnabled(True)
        self.status_label.setText("Status: Ready")
    
    def acquireData(self):
        with rwaveclient(host, port, verbose=True) as rwc:
            if rwc is None:
                return None
            # Configure acquisition
            rwc.send_cmd("start")
            rwc.send_cmd('swtrg 1024')
            rwc.send_cmd('readout')
            rwc.send_cmd('download')
            data = rwc.download()
            rwc.send_cmd('stop')
        
        return data
    
    def plotData(self, data):
        self.latest_data = data  # Store latest data for toggling
        self.plotWidget.clear()
        colors = ['yellow', 'cyan']
        
        if not data:
            return
        
        event = data[0]  # First acquired event
        x = np.arange(len(event[0]))
        
        for ch, color in zip(event.keys(), colors):
            if self.channel_visibility.get(ch, True):  # Check visibility
                y = event[ch]
                self.plotWidget.plot(x, y, pen=pg.mkPen(color, width=1), name=f'Channel {ch}', downsample=10, autoDownsample=True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = OscilloscopeApp()
    window.show()
    sys.exit(app.exec_())
