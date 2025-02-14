#!/bin/bash

# activating environment for Python
echo "Activating the virtual environment..."
source ../myenv/bin/activate

# running the server for the pulser and the digitizer
rnohup "/eu/aimtti/aimtti-server.py --address aimtti-tgp3152-00"
rnohup /eu/caen-dt5742b/soft/bin/rwaveserver