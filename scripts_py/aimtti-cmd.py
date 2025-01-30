#! /usr/bin/env python3

import socket
import argparse

### arguments

parser = argparse.ArgumentParser()
parser.add_argument('--address', type=str, required=True, help="IP address")
parser.add_argument('--cmd', type=str, required=True, help="Command")
args = vars(parser.parse_args())

SOCK='/tmp/tti_server_' + args['address'] + '.socket'
command = args['cmd']
try:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(SOCK)
        s.sendall(command.encode())
        data = s.recv(1024).decode()
        print(data)
except Exception as e:
    print(e)