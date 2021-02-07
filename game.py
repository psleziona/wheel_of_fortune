import socket
import threading
import select
import time
import random
import string
import pickle
import time
import random

class Message:

    def __init__(self, type_, content):
        self.type_ = type_
        self.content = content


class HandlePlayer:
    def __init__(self, username, sock, address, server):
        self.username = username
        self.sock = sock
        self.address = address
        self.game_id = None
        self.my_turn = False
        self.server = server

    def handle_connection(self):
        # ms = Message('server_msg', f'Witaj {self.username}')
        # self.message_sender(ms) zbudowanie klasy do obslugi wiadomosci 

        self.message_sender({'server_msg': f'Witaj {self.username}'})
        
        while True:
            try:
                data = pickle.loads(self.sock.recv(1024))
                self.server.message_handler(data, self)
            except EOFError:
                self.sock.close()
                self.server.remove_player(self)
                break

    def message_sender(self, msg):
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
            self.message_handler(
                {'server_msg': f'{username} connected.'}, player)

            if len(self.players) == 2:
                self.init_game()

        self.s.close()

    def message_handler(self, msg_object, player=None):
        for msg_type in msg_object.keys():
            if msg_type == 'chat_msg':
                self.handle_chat_msg(msg_object, player)
            elif msg_type == 'game_msg':
                game_obj = msg_object[msg_type]
                self.handle_game_action_msg(game_obj, player)
            elif msg_type == 'server_msg':
                self.handle_server_msg(msg_object, player)

    def handle_chat_msg(self, msg_object, player):
        data = msg_object['chat_msg']
        msg_object['chat_msg'] = f'<{player.username}> {data}'
        self.server_broadcast(msg_object, player)

    def handle_server_msg(self, msg_object, player):
        self.server_broadcast(msg_object, player)

    def handle_game_action_msg(self, game_object, player):
        game_id = player.game_id

        if game_object['type'] == 'get':
            self.games[game_id].handle_game_recv(
                game_object['content'], player)

        elif game_object['type'] == 'post':
            msg = game_object['content']
            to_other = game_object.get('multicast', False)
            if to_other:
                if to_other == 'with':
                    self.server_broadcast(msg, game=game_id) #all
                else:
                    self.server_broadcast(msg, player, game_id) # all without player
            else:
                self.server_broadcast(msg, player, single=True) # player


    def server_broadcast(self, msg, player=None, game=None, single=False):
        print(f'Msg: {msg} from {player} game {game} single {single}')
        if single and player: # player must be given
            player.message_sender(msg)
        else:
            for user in self.players.values():
                if (game and user.game_id != game) or (game and player and user.game_id != player.game_id) or (player and user == player):
                    continue
                user.message_sender(msg)

#################### USERS ##################################

    def check_username(self, username):
        if username in self.players:
            return True

    def remove_player(self, player):
        self.message_handler({'server_msg': f'{player.username} disconnected.'})
        del self.players[player.username]

#################### GAME ##################################

    def init_game(self):
        game_id = self.gen_id()

        for player in self.players.values():
            player.game_id = game_id

        game = Game(self, *self.players.values())
        self.games[game_id] = game
        game.game_init()

    def gen_id(self):
        g_id = ''
        for _ in range(5):
            g_id += random.choice(string.ascii_letters)
        return g_id


class Game:
    def __init__(self, server, *args):
        self.players = args
        self.player_stack = list(self.players)
        self.current_player = self.player_stack.pop()
        self.server = server

        self.password = self.get_password_from_file()
        self.chosen_letters = [' ']
        self.password_letters = set(self.password)
        self.gen_hidden_password()

    
    def get_password_from_file(self):
        with open('game_passwords.txt') as f:
            sentences = f.readlines()
            return random.choice(sentences)


    def create_game_object(self, content, multi, multi_with, player):
        game_msg = {'game_msg': {
            'type': 'post',
            'content': content
        }}
        if multi:
            game_msg['game_msg']['multicast'] = 'with' if multi_with else 'without'

        self.server.message_handler(game_msg, player)

    def create_game_action(self, action_type, content, multi=False, multi_with=False, player=None):
        if player is None:
            player = self.current_player
        data = {action_type: content}
        self.create_game_object(data, multi, multi_with, player)

    def game_init(self):
        self.create_game_action(
            'game_msg', f'Hello, let\'s start a game. On display u see hidden password. Game will start {self.current_player.username}', True, True)
        time.sleep(0.1)
        password = self.gen_hidden_password()
        self.create_game_action('game_password', password, True, True)
        time.sleep(0.1)
        self.create_game_action('get_letter', '')

    def game_round(self):
        if self.player_stack:
            self.current_player = self.player_stack.pop()
        else:
            self.player_stack = list(self.players)
            self.current_player = self.player_stack.pop()
        print(f'Nastepna runda dla: {self.current_player.username}')
        self.create_game_action('get_letter', '')

    def gen_hidden_password(self):
        return ''.join([x if x in self.chosen_letters else '_' for x in self.password])

    def handle_game_recv(self, game_obj, player):
        for action in game_obj.keys():
            if action == 'guess':
                guess = game_obj[action]
                if len(guess) == 1:
                    self.chosen_letters.append(guess)
                    self.check_letter(guess)
                else:
                    self.check_password(guess)
            elif action == 'chat_msg':
                content = f'<{player.username}> {game_obj[action]}'
                self.create_game_action('chat_msg', content, True, player=player)

    def check_password(self, password):
        if password == self.password:
            pass
        else:
            pass

    def check_letter(self, letter):
        if letter in self.password:
            pass
        else:
            pass
        password = self.gen_hidden_password()
        self.create_game_action('game_password', password, True, True)
        self.game_round()


if __name__ == '__main__':
    print('Server start')
    GameServer()
