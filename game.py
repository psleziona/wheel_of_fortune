import socket
import threading
import select
import time
import random
import string
import pickle
import time


class HandlePlayer:
    def __init__(self, username, sock, address, server):
        self.username = username
        self.sock = sock
        self.address = address
        self.game_id = None
        self.my_turn = False
        self.server = server

    def handle_connection(self):
        self.broadcast_message({'server_msg': f'Witaj {self.username}'})
        while True:
            try:
                data = pickle.loads(self.sock.recv(1024))
                self.server.message_handler(data, self)
            except EOFError:
                self.sock.close()
                self.server.remove_player(self)
                break

    def broadcast_message(self, msg):
        data = pickle.dumps(msg)
        self.sock.send(data)


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
            self.server_broadcast({'server_msg': f'{username} connected.'}, player)

            if len(self.players) == 2:
                self.init_game()

        self.s.close()


    def message_handler(self, msg_object, player=None):
        for msg_type in msg_object.keys():        
            if msg_type == 'chat_msg':
                data = msg_object['chat_msg']
                data = f'<{player.username}> {data}'
                self.server_broadcast(data, player)
            elif msg_type == 'game_action':
                id = player.game_id
                if self.games[id].handle_round(player, msg_object[msg_type]):
                    del self.games[id]
            elif msg_type == 'server_message':
                self.server_broadcast(msg_object)
            elif msg_type == 'get_letter':
                player.broadcast_message(msg_object)
        print(self.games)


    def server_broadcast(self, msg, player=None):
        for user in self.players.values():
            if player == user:
                continue
            user.broadcast_message(msg)


    def check_username(self, username):
        if username in self.players:
            return True

    def remove_player(self, player):
        del self.players[player.username]
        print(f'{player} removed')
        self.server_broadcast({'server_msg': f'{player.username} disconnected.'})

    def init_game(self):
        game = Game(self, *self.players.values())
        game_id = self.gen_id()

        for player in self.players.values():
            player.game_id = game_id

        self.games[game_id] = game

    def gen_id(self):
        g_id = ''
        for _ in range(5):
            g_id += random.choice(string.ascii_letters)
        return g_id
        

class Game:
    def __init__(self, server, *args):
        self.players = args
        self.password = 'ala ma kota'
        self.chosen_letters = [' ']
        self.password_letters = set(self.password)
        self.current_player = random.choice(self.players)
        self.server = server
        self.game_init()
        
    def game_init(self):
        self.show_sentence()
        time.sleep(0.1)
        self.server.message_handler({'get_letter': ''}, self.current_player)


    def show_sentence(self):
        password = ''.join([x if x in self.chosen_letters else '_' for x in self.password])
        self.server.server_broadcast({'game_display': password})

    def handle_round(self, player, letter):
        if len(letter) == 1:
            self.chosen_letters.append(letter)
        else:
            if letter.lower() == self.password:
                self.server.server_broadcast({'game_display': self.password})
                time.sleep(0.1)
                self.server.message_handler({'server_message': f'{self.current_player.username} won!'})
                return True
        for user in self.players:
            if player != user:
                self.current_player = user
        self.game_init()

        

GameServer()
