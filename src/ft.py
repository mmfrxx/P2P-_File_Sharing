from __future__ import print_function
import os
import socket
import sys
from threading import Thread

from utils import send_msg, save_files_dict, construct_file_str_1, json_save, json_load

config = {}
config_file = "config.json"
clients_file = "clients.json"
clients = {}
conn_clients = {}

all_files = {}


def communicate(conn, client, buffer, prev_cmd):
    global config
    global config_file
    global all_files

    if "\0" not in buffer:
        return "", prev_cmd
    else:
        idx = buffer.index("\0")
        msg = buffer[:idx-1]
        buffer = buffer[idx+1:]

    # message split
    lines = msg.split("\n")
    fields = lines[0].split(" ")
    cmd = fields[0]
    if cmd == "HELLO":
        config['uoffset'] += 1
        json_save(config_file, config)

        conn_clients[client] = "u" + str(config['uoffset'])
        if conn_clients[client] not in clients:
            clients[conn_clients[client]] = {}

        clients[conn_clients[client]]['host'] = fields[1]
        clients[conn_clients[client]]['port'] = fields[2]
        clients[conn_clients[client]]['is_connected'] = 1
        # json_save(clients_file, clients)

        send_msg(conn, "HI {}\n\0".format(conn_clients[client]))
        return communicate(conn, client, buffer, "HI")
    elif cmd == "LIST":
        if conn_clients[client] not in clients:
            clients[conn_clients[client]] = {}

        clients[conn_clients[client]]['files'] = lines[1:]

        save_files_dict(all_files, lines[1:])
        print("ALL FILES")
        print(all_files)
        json_save(clients_file, clients)

        send_msg(conn, "ACCEPTED\n\0")
        return buffer, "ACCEPTED"

    elif cmd == "SEARCH:":
        filename = fields[1]
        if filename in all_files:
            msg = "FOUND: \n"
            prev_cmd = "FOUND"
            for file in all_files[filename]:
                if clients[file['client'][:-1]]['is_connected']:
                    msg += construct_file_str_1(file) + "\n"
            msg += "\0"
        else:
            msg = "NOT_FOUND\n\0"
            prev_cmd = "NOT_FOUND"

        send_msg(conn, msg)
        return buffer, prev_cmd

    elif cmd == "BYE":
        print("should update connected clients\n")
        clients[conn_clients[client]]['is_connected'] = 0
        json_save(clients_file, clients)
        send_msg(conn, "BYE\n\0")
        return buffer, prev_cmd

    else:
        print("invalid command was received\n")
        send_msg(conn, "ERROR\n\0")
        sys.exit(-1)



def serve(conn, addr):
    buffer = ""
    prev_cmd = ""

    while True:
        msg = conn.recv(4096).decode("utf-8")
        print("received message: ", msg)
        if len(msg) == 0:
            break
        else:
            buffer += msg

        buffer, prev_cmd = communicate(conn, addr, buffer, prev_cmd)
        

def main():
    global config
    global config_file

    config_file = "config.json"

    if os.path.isfile(config_file):
        config = json_load(config_file)
    else:
        config['host'] = 'localhost'
        config['port'] = 45002
        config['uoffset'] = 0
        json_save(config_file, config)

    # creating socket for connection
    try:
        ssock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print("failed to create socket\n")
        sys.exit(-1)

    host = config['host']
    port = config['port']

    # bind socket
    try:
        ssock.bind((host, port))
    except socket.error:
        print("failed to bind socket\n")
        sys.exit(-1)

    # listen for connections
    ssock.listen(5)

    ccount = 0
    while True:
        conn, addr = ssock.accept()
        # creating thread for each client
        cthread = Thread(name="client_"+str(ccount), target=serve, args=(conn, addr))
        cthread.daemon = True
        cthread.start()
        ccount += 1


if __name__ == "__main__":
    main()
