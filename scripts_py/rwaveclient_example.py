import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget, QVBoxLayout, QPushButton
import pyqtgraph as pg
from rwave import rwaveclient
import threading

host = 'localhost'
port = 30001

class OscilloscopeApp(QWidget):
    def __init__(self):
        super().__init__()
        self.host = 'localhost'  # Aggiungi questa riga
        self.port = 30001  # Aggiungi questa riga
        self.current_frequency = 750
        self.initUI()
        
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

    
    def initUI(self):
        layout = QVBoxLayout()
        self.setWindowTitle("Digitizer Control")
        self.setGeometry(100, 100, 800, 600)
        
        # Graph widget
        self.plotWidget = pg.PlotWidget()
        self.plotWidget.setBackground('black')
        self.plotWidget.showGrid(x=True, y=True)
        self.plotWidget.addLegend()
        
        # Configure axes
        self.plotWidget.setLabel('left', 'Amplitude')
        self.plotWidget.setLabel('bottom', 'Samples')
        
        layout.addWidget(self.plotWidget)
        
        # Button
        self.button = QPushButton('Start Acquisition')
        self.button.clicked.connect(self.startAcquisition)
        layout.addWidget(self.button)
        
        self.freq_buttons = []
        for freq in [750, 1000, 2500, 5000]:  # Frequencies in MHz
            btn = QPushButton(f"{freq} MHz", self)
            btn.clicked.connect(lambda _, f=freq: self.set_frequency(f))
            self.freq_buttons.append(btn)
            
        freq_layout = QHBoxLayout()
        for btn in self.freq_buttons:
            freq_layout.addWidget(btn)
        layout.addLayout(freq_layout)
        
        self.setLayout(layout)
        self.setWindowTitle("Oscilloscope Viewer")
    
    def startAcquisition(self):
        self.button.setEnabled(False)
        data = self.acquireData()
        if data:
            self.plotData(data)
        self.button.setEnabled(True)
    
    
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
        self.plotWidget.clear()
        colors = ['yellow', 'cyan']
        
        # Plot first event only (modify as needed)
        event = data[0]  # Primo evento acquisito
        x = np.arange(len(event[0]))
        
        for ch, color in zip(event.keys(), colors):
            y = event[ch]
            self.plotWidget.plot(x, y, pen=pg.mkPen(color, width=2), name=f'Channel {ch}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = OscilloscopeApp()
    window.show()
    sys.exit(app.exec_())