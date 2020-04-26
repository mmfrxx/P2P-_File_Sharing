from __future__ import print_function
import json
import os
import socket
import sys
import time
from threading import Thread
from tkinter import *
import tkinter as tk
import os
import time

try:
    import queue as Queue
except ImportError:
    import Queue

from utils import send_msg, json_save, json_load, construct_file_str
from peer import communicate, listen, accept_peer, give_peer, download_from_peer

config = {}
config_file = "config.json"
clients = {}
client_file = "clients.json"


def init_conn(addr):
    host, port = addr
    try:
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("creating socket init_conn")
    except socket.error:
        print("failed to create socket\n")
        sys.exit(-1)

    try:
        conn.connect((host, port))
        print("connecting init_conn")
    except socket.error:
        print("failed to connect to port: {}\n".format(port))
        print("failed to connect to host: {}\n".format(host))
        sys.exit(-1)

    return conn


class ParentWindow(Frame):
    def __init__(self, master, *args, **kwargs):
        Frame.__init__(self, master, *args, **kwargs)

        self.master = master
        self.master.minsize(500, 230)
        self.master.title("P2P File Transfer")
        self.database = []
        self.server_files = []
        self.server = None
        self.buffer = ""
        self.client = ""
        self.files = 0
        self.lsock = None
        self.lhost = "127.0.0.1"
        self.lport = 36360
        self.searched_files_list = []
        self.selected_file = ""

    def start(self):
        global config
        global config_file
        global client_file
        global clients

        config_file = "config.json"
        client_file = "clients.json"

        if os.path.isfile(config_file):
            with open(config_file, "rb") as file:
                config = json.load(file)
        else:
            config['host'] = 'localhost'
            config['port'] = 45002
            json_save(config_file, config)

        # connect with server
        self.server = init_conn((config['host'], config['port']))

        # open listening port for peers
        queue = Queue.Queue()

        self.lsock = listen(queue)
        self.lhost, self.lport = queue.get()

        lthread = Thread(name="lthread", target=accept_peer, args=(self.lsock,))
        lthread.daemon = True
        lthread.start()

        greeting = tk.Label(text="Please provide at least one file to server.\n\r")
        greeting.pack()
        self.add_file()

    def add_file(self):
        custom_source = StringVar()
        custom_source.set('Provide a path to the file in folder \'SharedP2P\' please. Example: ./SharedP2P/filename ')
        text_source = tk.Entry(self.master, width=90, textvariable=custom_source)
        text_source.pack()

        def check():
            file_path = text_source.get()
            if os.path.isfile(file_path):
                add_button['state'] = 'disabled'
                add_button.pack_forget()
                self.files += 1
                self.get_info_about_file(file_path)
                return
            else:
                text_source.delete(0, tk.END)
                text_source.insert(0, "Path is invalid. Provide another.")

        add_button = tk.Button(text="Add", width=3, height=1, bg="white", fg="black", command=check)
        add_button.pack()

    def get_info_about_file(self, file_path):
        global shared_files_list

        repo, name = file_path.split("/")[1:]
        name, ext = os.path.splitext(name)
        path = os.path.abspath(os.getcwd()) + "/" + repo
        # name, ext  = os.path.splitext(file_path[2:])
        size = os.path.getsize(file_path)
        modified = os.path.getmtime(file_path)
        year, month, day, hour, minute, second = time.localtime(modified)[:-3]
        date = "%02d/%02d/%d" % (day, month, year)
        print(path + "\n" + name + "\n" + ext)

        self.database.append([name, path, ext, size, date])
        self.loop()

    def loop(self):
        if self.files < 5:
            want_more = tk.Label(text="Do you want to add another file?")
            want_more.pack()

            def forget():
                want_more.pack_forget()
                yes.pack_forget()
                no.pack_forget()

            def yes_func():
                forget()
                self.add_file()

            def no_func():
                forget()
                self.send()

            yes = tk.Button(text="Yes", width=3, height=1, bg="white", fg="black", command=yes_func)
            yes.pack()
            no = tk.Button(text="No", width=3, height=1, bg="white", fg="black", command=no_func)
            no.pack()

        else:
            self.send()

    def send(self):
        ##########################################################3
        # send "HELLO" to server
        send_msg(self.server, "HELLO {} {}\n\0".format(self.lhost, self.lport))
        print("I HAVE SENT MSG HELLO")
        lines = communicate(self.server, self.buffer)
        fields = lines[0].split(" ")
        cmd = fields[0]
        # [name, path, ext, size, date]
        if cmd == "HI":
            client_name = fields[1]
            list_msg = "LIST \n"
            for file in self.database:
                file_str = construct_file_str(file, client_name)
                list_msg += file_str + "\n"
            list_msg += "\0"
            send_msg(self.server, list_msg)

        print("my buffer: ", self.buffer)
        lines = communicate(self.server, self.buffer)
        fields = lines[0].split(" ")
        cmd = fields[0]

        print("received ", cmd)
        if cmd == "ACCEPTED":
            self.search()

    def search(self):
        custom_source = StringVar()
        custom_source.set('Which file do you want to download? Provide just a name.')
        text_source = tk.Entry(self.master, width=60, textvariable=custom_source)
        text_source.pack()

        def check():
            self.selected_file = text_source.get()
            ##########################################################3

            msg = "SEARCH: " + self.selected_file + "\n\0"
            send_msg(self.server, msg)

            lines = communicate(self.server, self.buffer)
            fields = lines[0].split(" ")
            cmd = fields[0]

            

            if cmd == "FOUND:":
                for line in lines[1:]:
                    self.server_files.append(line)

            if len(self.server_files) == 0:
                self.server_files = []
                text_source.delete(0, tk.END)
                text_source.insert(0, "This file does not exist. Provide another.")
            else:
                exit_button.pack_forget()
                search_button['state'] = 'disabled'
                self.download_file()
                return
        
        
        def exitt():
            send_msg(self.server, "BYE\n\0")
            self.master.quit() 
        
        search_button = tk.Button(text="Search", width=5, height=1, bg="white", fg="black", command=check)
        search_button.pack()
        exit_button = tk.Button(text="Exit", width=5, height=1, bg="white", fg="black", command=exitt)
        exit_button.pack()
            

    def download_file(self):
        print("GUI download file")
        select_file = tk.Label(text="Please, select the file you want to download.")
        select_file.pack()

        scrollbar = tk.Scrollbar(self.master)
        scrollbar.pack(side=RIGHT, fill=Y)

        mylist = Listbox(self.master, yscrollcommand=scrollbar.set)
        for i in range(len(self.server_files)):
            mylist.insert(END, self.server_files[i])

        scrollbar.config(command=mylist.yview)
        mylist.pack(fill=BOTH)

        def download():
            print("GUI download")
            download_button['state'] = 'disabled'
            #self.master.quit()
            selected = mylist.get(mylist.curselection())
            ##########################################################3


            requested_file = selected.split(", ")
            peer_client = requested_file[4][:-1]

            print("PEER CLIENT: ", peer_client)
            client = json_load(client_file)[peer_client]

            peer_host = client['host']
            peer_port = int(client['port'])

            peer_connected = int(client['is_connected'])
            if peer_connected:
                print("peer is connected")
                print("lhost: ", peer_host)
                print("lport: ", peer_port)

                peer = init_conn((peer_host, peer_port))
                give_peer(peer, self.selected_file, requested_file)
            else:
                print("peer is not connected")

            
            select_file.pack_forget()
            mylist.pack_forget()
            download_button.pack_forget()
            scrollbar.pack_forget()
            self.server_files = []
            self.search()
            #download_from_peer(self.lhost, self.lport, self.selected_file, requested_file)

          

        download_button = tk.Button(text="Download", width=5, height=1, bg="white", fg="black", command=download)
        download_button.pack()

    
  

if __name__ == "__main__":
    root = tk.Tk()
    App = ParentWindow(root)
    App.start()
    root.mainloop()
