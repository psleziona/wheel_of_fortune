import socket
import select
import sys


class Client:

    def __init__(self, name):
        self.name = name
        self.connect_to_server()


    def connect_to_server(self):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect(('127.0.0.1', 9000))
            self.s.send(self.name.encode())
            self.handle_connection()
        except:
            print('Server does not respond')


    def handle_connection(self):
        while True:
            r, _, _ = select.select([self.s, sys.stdin], [], [])
            for streams in r:
                if streams == self.s:
                    data = self.s.recv(1024).decode()
                    print(data)
                    if not data:
                        sys.exit()
                else:
                    msg = input()
                    self.s.send(msg.encode())



name = input('Enter name: ')
Client(name)