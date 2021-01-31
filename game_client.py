import sys, socket, select, time, pickle
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow


class ConnectionHandler(QThread):
    finished = pyqtSignal()
    msg = pyqtSignal(object)

    def __init__(self, name):
        super().__init__()
        self.name = name

    def run(self):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect(('127.0.0.1', 9000))
            self.s.send(self.name.encode())
        except:
            print('Failed')
        while True:
            data = pickle.loads(self.s.recv(1024))
            self.msg.emit(data)
            if not data:
                self.finished.emit()
                break

    def msg_sender(self, msg):
        data = pickle.dumps(msg)
        self.s.send(data)


class ClientWindow(QMainWindow):
    sender = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.chat_messages = ''
        self.sending_letter = False
        self.setGeometry(100, 100, 900, 640)
        self.setWindowTitle('Game Client')
        self.setupUI()

    def setupUI(self):
        self.nameField = QtWidgets.QTextEdit(self)
        self.nameField.setGeometry(QtCore.QRect(10, 10, 141, 31))
        self.nameField.setObjectName("nameField")

        self.startBtn = QtWidgets.QPushButton(self)
        self.startBtn.setGeometry(QtCore.QRect(160, 10, 141, 30))
        self.startBtn.setObjectName("startBtn")

        self.gameDisplay = QtWidgets.QTextBrowser(self)
        self.gameDisplay.setGeometry(QtCore.QRect(10, 50, 571, 192))
        self.gameDisplay.setObjectName("gameDisplay")

        self.serverDisplay = QtWidgets.QTextBrowser(self)
        self.serverDisplay.setGeometry(QtCore.QRect(10, 260, 571, 192))
        self.serverDisplay.setObjectName("serverDisplay")

        self.msgField = QtWidgets.QTextEdit(self)
        self.msgField.setGeometry(QtCore.QRect(10, 560, 471, 70))
        self.msgField.setObjectName("msgField")

        self.sendBtn = QtWidgets.QPushButton(self)
        self.sendBtn.setGeometry(QtCore.QRect(490, 580, 89, 25))
        self.sendBtn.setObjectName("sendBtn")
        self.sendBtn.clicked.connect(self.handle_sends)

        self.startBtn.setText("Start game")
        self.startBtn.clicked.connect(self.get_name)
        self.sendBtn.setText("Send")

    def get_name(self):
        self.startBtn.setEnabled(False)
        self.username = self.nameField.toPlainText()
        self.client = ConnectionHandler(self.username)
        self.client.msg.connect(self.handle_recv)
        self.sender.connect(self.client.msg_sender)
        self.client.start()

    def handle_recv(self, msg):
        print(msg)
        try:
            for msg_types in msg.keys():
                if msg_types == 'chat_msg':
                    self.chat_messages += msg[msg_types] + '\n'
                elif msg_types == 'server_msg':
                    self.chat_messages += f'<Server> {msg[msg_types]}' + '\n'
                elif msg_types == 'game_password':
                    self.game_display(msg[msg_types])
                elif msg_types == 'game_msg':
                    self.chat_messages += f'<Game> {msg[msg_types]}' + '\n'
                elif msg_types == 'get_letter':
                    self.choose_letter()
        except AttributeError:
            self.chat_messages += msg
        self.update_display()

    def handle_sends(self, send_letter):
        msg = self.msgField.toPlainText()
        if self.sending_letter:
            self.create_game_action('guess', msg)
            self.sending_letter = False
        else:
            self.create_game_action('chat_msg', msg)
            self.chat_messages += f'<You> {msg}' + '\n'
            self.update_display()
        self.msgField.setText('')

    def update_display(self):
        self.serverDisplay.setText(self.chat_messages)

    def game_display(self, display):
        self.gameDisplay.setText(display)

    def choose_letter(self):
        self.msgField.setText('Please type your letter or guess password: ')
        self.sending_letter = True

    def create_game_action(self, action, content):
        self.create_game_object({action: content})

    def create_game_object(self, data):
        game_obj = {'game_msg': {
            'type': 'get',
            'content': data # {action: msg}
        }}
        self.sender.emit(game_obj)


app = QApplication(sys.argv)
win = ClientWindow()

win.show()
sys.exit(app.exec_())
