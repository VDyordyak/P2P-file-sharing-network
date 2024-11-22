from socket import *
from select import *
from threading import *
from torrent_error import *
from torrent_logger import *
import sys

class peer_socket():
    def __init__(self, peer_IP, peer_port, psocket=None):
        if psocket is None:
            self.peer_sock = socket(AF_INET, SOCK_STREAM)
            self.peer_connection = False
        else:
            self.peer_connection = True
            self.peer_sock = psocket
        self.timeout = 3
        self.peer_sock.settimeout(self.timeout)
        self.IP = peer_IP
        self.port = peer_port
        self.unique_id = self.IP + ' ' + str(self.port)
        self.max_peer_requests = 50
        self.socket_lock = Lock()
        self.socket_logger = torrent_logger(self.unique_id, SOCKET_LOG_FILE, DEBUG)

    def recieve_data(self, data_size):
        if not self.peer_connection:
            return
        peer_raw_data = b''
        recieved_data_length = 0
        request_size = data_size
        while(recieved_data_length < data_size):
            try:
                chunk = self.peer_sock.recv(request_size)
            except:
                chunk = b''
            if len(chunk) == 0:
                return None
            peer_raw_data += chunk
            request_size -= len(chunk)
            recieved_data_length += len(chunk)
        return peer_raw_data 

    def send_data(self, raw_data):
        if not self.peer_connection:
            return False
        data_length_send = 0
        while(data_length_send < len(raw_data)):
            try:
                data_length_send += self.peer_sock.send(raw_data[data_length_send:])
            except:
                return False
        return True

    def start_seeding(self):
        try:
            self.peer_sock.bind((self.IP, self.port))
            self.peer_sock.listen(self.max_peer_requests)
        except Exception as err:
            binding_log = 'Seeding socket binding failed ! ' + self.unique_id + ' : '
            self.socket_logger.log(binding_log + err.__str__())
            sys.exit(0)

    def request_connection(self):
        try:
            self.peer_sock.connect((self.IP, self.port))
            self.peer_connection = True
        except Exception as err:
            self.peer_connection = False
            connection_log = 'Socket connection failed for ' + self.unique_id + ' : '
            self.socket_logger.log(connection_log + err.__str__())
        return self.peer_connection

    def accept_connection(self):
        connection_log = ''
        try:
            connection = self.peer_sock.accept()
            connection_log += 'Socket connection recieved !'
        except Exception as err:
            connection = None
            connection_log = 'Socket accept connection for seeder ' + self.unique_id + ' : ' 
            connection_log += str(err)
        self.socket_logger.log(connection_log)
        return connection

    def peer_connection_active(self):
        return self.peer_connection

    def disconnect(self):
        self.peer_sock.close()
        self.peer_connection = False

    def __exit__(self):
        self.disconnect()