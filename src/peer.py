from __future__ import print_function
import json
import os
import random
import signal
import socket
import sys
import time
from threading import Thread

try:
    import queue as Queue
except ImportError:
    import Queue

from utils import send_msg, json_save, json_load


def communicate(server, buffer):
    if "\0" not in buffer:
        msg = server.recv(4096).decode("utf-8")
        print("received message: ", msg)
        buffer += msg
        return communicate(server, buffer)
    else:
        idx = buffer.index("\0")
        msg = buffer[:idx-1]
        buffer = buffer[idx+1:]

    return msg.split("\n")


def give_peer(peer, searched_file, requested_file):
    print("GIVE PEER .....")
    requested_file_str = ""
    for rf in requested_file:
        requested_file_str += rf + ","

    # print("req_file")
    print(requested_file)
    print("req_file_str")
    
    
    send_msg(peer, "DOWNLOAD: {} {}\n\0".format(searched_file, requested_file_str))
    print("sent msg DOWNLOAD")
    buffer = ""

    while "\0" not in buffer:
        buffer += peer.recv(4096).decode("utf-8")
        print("received from buffer_1: ", buffer)

    idx = buffer.index("\0")
    msg = buffer[:idx]
    buffer = buffer[idx + 1:]

    fields = msg.split("\n")
    cmd = fields[0]
    if cmd == "FILE:":
        print("DOWNLOADED THE FILE")

        field_str = ""
        for field in fields[1:]:
            field_str += field + "\n"
        file_data = field_str.encode()
        downloaded_file_path = "./downloaded_files/"

        if os.path.exists(downloaded_file_path):
            print("Path exists")

            req_file_type = requested_file[1]

            file_ = downloaded_file_path + searched_file + req_file_type

            file_to_save = open(file_, "wb")
            file_to_save.write(file_data)
            file_to_save.close()

        send_msg(peer, "THANKS\n\0")
        peer.close()
        return

    elif cmd == "ERROR":
        print("here in ERROR")
        return

    else:
        print("invalid command received: \n", cmd)
        # sys.exit(-1)
        return


def download_from_peer(conn, addr):
    buffer = ""

    print("download_from_peer()")

    while True:
        while "\0" not in buffer:
            buffer += conn.recv(4096).decode("utf-8")

        print("received from peer_2: ", buffer)
        idx = buffer.index("\0")
        msg = buffer[:idx-1]
        buffer = buffer[idx+1:]

        fields = msg.split()
        cmd = fields[0]

        if cmd == "DOWNLOAD:":
            print("SENT FILE TO DOOWNLOAD")
            msg = "FILE:\n"
            conn.send(msg.encode())
            print("FIELDSSSSSSSSSSSSSSSSSS")
            print(fields)
            searched_file = fields[1]
            requested_file = fields[2].split(",")
            print("REQUESTEED FILE")
            print(requested_file)
            req_file_path = requested_file[0][1:]
            req_file_type = requested_file[1]

            file_ = req_file_path + "/" + searched_file + req_file_type
            file__ = open(file_, "rb")

            file_buffer = file__.read(1024)
            while file_buffer:
                conn.send(file_buffer)
                file_buffer = file__.read(1024)

            conn.send("\0".encode())
            file__.close()

        else:
            print("undetermined error BLA BLA\n")
        return


def listen(queue):
    try:
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print("failed to create socket\n")
        sys.exit(-1)

    lsock.listen(5)
    lport = lsock.getsockname()[1]
    print(lport)

    queue.put(('localhost', lport))
    return lsock


def accept_peer(lsock):
    pcount = 0
    while True:
        conn, addr = lsock.accept()
        pthread = Thread(name="p" + str(pcount), target=download_from_peer, args=(conn, addr))

        pthread.daemon = True
        pthread.start()
        pcount += 1
        print("\n!!! in LISTEN while loop !!!\n")


if __name__ == '__main__':
    queue = Queue.Queue()
    listen(queue)