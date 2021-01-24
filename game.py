import socket
import threading
import select
import time
import random
import string


class HandlePlayer:
    def __init__(self, username, socket, address, server):
        self.username = username
        self.socket = socket
        self.address = address
        self.in_game = False
        self.my_turn = False
        self.server = server
        self.incoming = []

    def handle_connection(self):
        while True:
            data = self.socket.recv(1024).decode()
            if len(data) == 0:
                self.socket.close()
                self.server.remove_player(self)
                break
            self.incoming.append(data)
            # self.handle_data(data)

    def handle_data(self, data):
        print(data)

    def broadcast_message(self, msg):
        self.socket.send(msg.encode())


class GameServer:
    def __init__(self):
        self.players = {}
        self.games = {}
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.s.bind(('127.0.0.1', 9000))
        self.s.listen(10)

        while True:
            conn, address = self.s.accept()
            username = conn.recv(1024).decode()
            if self.check_username(username):
                conn.send(b'Nick already in use')
                conn.close()
                continue
            player = HandlePlayer(username, conn, address, self)
            threading._start_new_thread(player.handle_connection, ())
            self.players[username] = player
            if len(self.players) == 2:
                self.init_game()
        self.s.close()

    def check_username(self, username):
        if username in self.players:
            return True

    def remove_player(self, player):
        del self.players[player.username]
        print(f'{player.username} disconnected!')
        print(self.players)

    def init_game(self):
        game = Game(*self.players.values())
        for player in self.players.values():
            player.in_game = True
        game_id = self.gen_id()
        self.games[game_id] = game

    def gen_id(self):
        g_id = ''
        for _ in range(5):
            g_id += random.choice(string.ascii_letters)
        return g_id
        


class Game:
    def __init__(self, *args):
        self.players = args
        self.already_played = []
        self.password = 'ala ma kota'
        self.chosen_letters = [' ']
        self.password_letters = set(self.password)
        self.current_player = None
        self.broadcast(['Let\'s begin'])
        self.choose_begining_player()

    
    def handle_game(self):
        while True:
            pass

    def show_sentence(self):
        return ''.join([x if x in self.chosen_letters else '_' for x in self.password])

    def choose_letter(self, letter):
        self.chosen_letters.append(letter)

    def broadcast(self, msgs):
        for player in self.players:
            for msg in msgs:
                player.socket.send(msg.encode())

    def choose_begining_player(self):
        player = random.choice(self.players)
        self.current_player = player
        self.broadcast([ self.show_sentence(), f'Current user is {self.current_player.username}'])
        self.round()

    def round(self):
        self.current_player.socket.send(b'Type your letter')
        while not self.current_player.incoming:
            continue
        for msg in self.current_player.incoming:
            self.choose_letter(msg)
        self.current_player.incoming = []
        self.broadcast([self.show_sentence()])
        self.after_round()

    def next_round(self):
        self.already_played = []
        self.choose_begining_player()
    
    def after_round(self):
        self.already_played.append(self.current_player)
        if self.check_all_played():
            return self.next_round()
        for player in self.players:
            if player != self.current_player:
                self.current_player = player
                break
        self.round()

    
    def check_all_played(self):
        return len(self.players) == len(self.already_played)


GameServer()
