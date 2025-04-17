#!/bin/bash

# Uso: ./scan_voltages.sh start end step sampling
# Esempio: ./scan_voltages.sh 23 29 1 1024

if [ "$#" -ne 4 ]; then
  echo "Uso: $0 start_voltage end_voltage step sampling"
  exit 1
fi

start_voltage=$1
end_voltage=$2
step=$3
sampling=$4

host="aimtti-plh120p-00"
port=9221

voltage=$start_voltage

while (( $(echo "$voltage <= $end_voltage" | bc -l) )); do
  echo "----------------------------------------"
  echo "Imposto V1 a ${voltage} V"
  echo "V1 $voltage" | nc -w1 -W1 "$host" "$port"
  sleep 1

  echo "Eseguo: run_dgz.py con vbias=${voltage}V e sampling=${sampling}"
  python run_dgz.py --filter_ADC 6 --channel 1 --sampling "$sampling" --min_events 80000 --vbias "$voltage"

  voltage=$(echo "$voltage + $step" | bc)
done
