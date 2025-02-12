#!/bin/bash
# 2025-02-12, Riccardo Ricci
# usage:  
#   source configure.sh # to activate the virtual environment
#   source configure.sh --servers # to activate the virtual environment and start the servers


# Activating environment for Python
echo "Activating the virtual environment..."
source ../myenv/bin/activate

# Check for the flag --start-servers
if [[ "$1" == "--servers" ]]; then
    echo "Starting servers..."
    nohup /eu/aimtti/aimtti-server.py --address aimtti-tgp3152-00 &
    nohup /eu/caen-dt5742b/soft/bin/rwaveserver &
else
    echo "Skipping server startup."
fi
