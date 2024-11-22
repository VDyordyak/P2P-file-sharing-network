import sys
import time
import struct
import hashlib
from threading import *
from copy import deepcopy


from torrent_error import torrent_error
from torrent_logger import *
from peer_wire_messages import *
from shared_file_handler import torrent_shared_file_handler
from peer_socket import *
from peer_state import *

class peer():
    
    def __init__(self, peer_IP, peer_port, torrent, init_peer_socket = None):
        
        self.IP         = peer_IP
        self.port       = peer_port
        self.torrent    = deepcopy(torrent)
        
        
        self.state = peer_state()

        
        self.unique_id  = '(' + self.IP + ' : ' + str(self.port) + ')'
        
        
        self.peer_id = None

        
        self.max_block_length = torrent.block_length
        
        
        self.handshake_flag = False
        
        
        self.bitfield_pieces = set([])
        
        
        self.peer_sock = peer_socket(self.IP, self.port, init_peer_socket)
            
        
        self.file_handler = None

        
        logger_name = 'peer' + self.unique_id
        self.peer_logger = torrent_logger(logger_name, PEER_LOG_FILE, DEBUG)
        if torrent.client_request['seeding'] != None:
            self.peer_logger.set_console_logging()

        
        self.response_handler = { KEEP_ALIVE    : self.recieved_keep_alive,
                                  CHOKE         : self.recieved_choke,
                                  UNCHOKE       : self.recieved_unchoke,
                                  INTERESTED    : self.recieved_interested,
                                  UNINTERESTED  : self.recieved_uninterested,
                                  HAVE          : self.recieved_have, 
                                  BITFIELD      : self.recieved_bitfield,
                                  REQUEST       : self.recieved_request,
                                  PIECE         : self.recieved_piece,
                                  CANCEL        : self.recieved_cancel,
                                  PORT          : self.recieved_port }

        
        self.keep_alive_timeout = 10
        
        self.keep_alive_timer = None

    def initialize_seeding(self):
        
        self.peer_sock.start_seeding()

    def set_bitfield(self):
        for i in range(self.torrent.pieces_count):
            self.bitfield_pieces.add(i)

    def recieve_connection(self):
        return self.peer_sock.accept_connection()

    def send_connection(self):
        connection_log = 'SEND CONNECTION STATUS : ' + self.unique_id + ' '
        connection_status = None
        if self.peer_sock.request_connection():
            
            connection_log += SUCCESS
            connection_status = True
        else:
            
            connection_log += FAILURE 
            connection_status = False
         
        self.peer_logger.log(connection_log)
        return connection_status

    def close_peer_connection(self):
        self.state.set_null()
        self.peer_sock.disconnect()

    def recieve(self, data_size):
        return self.peer_sock.recieve_data(data_size)

    def send(self, raw_data):
        if not self.peer_sock.send_data(raw_data):
            send_log = self.unique_id +  ' peer connection closed ! ' + FAILURE
            self.peer_logger.log(send_log)
            self.close_peer_connection()

    def send_message(self, peer_request):
        if self.handshake_flag:
            
            peer_request_log = 'sending message  -----> ' + peer_request.__str__() 
            self.peer_logger.log(peer_request_log)
            
            self.send(peer_request.message())

    def recieve_message(self):
        
        
        raw_message_length = self.recieve(MESSAGE_LENGTH_SIZE)
        if raw_message_length is None or len(raw_message_length) < MESSAGE_LENGTH_SIZE:
            return None

        
        message_length = struct.unpack_from("!I", raw_message_length)[0]
        
        if message_length == 0:
            return peer_wire_message(message_length, None, None)

        
        raw_message_ID =  self.recieve(MESSAGE_ID_SIZE)
        if raw_message_ID is None:
            return None
        
        
        message_id  = struct.unpack_from("!B", raw_message_ID)[0]
        
        if message_length == 1:
            return peer_wire_message(message_length, message_id, None)
       
        
        payload_length = message_length - 1
        
        
        message_payload = self.recieve(payload_length)
        if message_payload is None:
            return None
        
        
        self.keep_alive_timer = time.time()
        
        return peer_wire_message(message_length, message_id, message_payload)

    def initiate_handshake(self):
        
        if not self.handshake_flag and self.send_connection():
            
            handshake_request = self.send_handshake()
            
            raw_handshake_response = self.recieve_handshake()
            if raw_handshake_response is None:
                return False
            
            handshake_response = self.handshake_validation(raw_handshake_response)
            if handshake_response is None:
                return False
            
            self.peer_id = handshake_response.client_peer_id
            self.handshake_flag = True
            
            return True
        
        return False

    def respond_handshake(self):
        
        if self.handshake_flag:
            return True
        
        self.keep_alive_timer = time.time()
        
        while not self.check_keep_alive_timeout():
            raw_handshake_response = self.recieve_handshake()
            if raw_handshake_response is not None:
                break
        
        if raw_handshake_response is None:
            return False
        
        handshake_response = self.handshake_validation(raw_handshake_response)
        if handshake_response is None:
            return False 
        
        self.peer_id = handshake_response.client_peer_id
        
        self.send_handshake()
        self.handshake_flag = True
        
        return True

    def build_handshake_message(self):
        info_hash = self.torrent.torrent_metadata.info_hash
        peer_id   = self.torrent.peer_id
        
        return handshake(info_hash, peer_id)

    def send_handshake(self):
        
        handshake_request = self.build_handshake_message()
        
        self.send(handshake_request.message())
        
        
        handshake_req_log = 'Handshake initiated -----> ' + self.unique_id
        self.peer_logger.log(handshake_req_log)
        
        
        return handshake_request

    def recieve_handshake(self):
        
        raw_handshake_response = self.recieve(HANDSHAKE_MESSAGE_LENGTH)
        if raw_handshake_response is None:
            
            handshake_res_log = 'Handshake not recived from ' + self.unique_id
            self.peer_logger.log(handshake_res_log)
            return None
        
        
        handshake_res_log = 'Handshake recived   <----- ' + self.unique_id
        self.peer_logger.log(handshake_res_log)
        
        
        return raw_handshake_response

    def handshake_validation(self, raw_handshake_response):
        
        validation_log = 'Handshake validation : '
        try:
            handshake_request = self.build_handshake_message()
            handshake_response = handshake_request.validate_handshake(raw_handshake_response)
            validation_log += SUCCESS
            
            self.peer_logger.log(validation_log)
            return handshake_response
        except Exception as err_msg:
            validation_log += FAILURE + ' ' + err_msg.__str__()
            
            self.peer_logger.log(validation_log)
            return None

    def initialize_bitfield(self):
        
        if not self.peer_sock.peer_connection_active():
            return self.bitfield_pieces
        
        if not self.handshake_flag:
            return self.bitfield_pieces
        
        messages_begin_recieved = True
        while(messages_begin_recieved):
            
            response_message = self.handle_response()
            
            if response_message is None: 
                messages_begin_recieved = False
        
        return self.bitfield_pieces

    def get_handshake_log(self):
        log = 'HANDSHAKE with ' + self.unique_id + ' : '
        if self.handshake_flag:
            log += SUCCESS + '\n'
        else:
            log += FAILURE + '\n'
        peer_bitfield_count = len(self.bitfield_pieces)
        log += 'COUNT BITFIELDs with ' + self.unique_id + ' : '
        if peer_bitfield_count == 0:
            log += 'did not recieved !'
        else:
            log += str(peer_bitfield_count) + ' pieces'
        return log

    def handle_response(self):
        
        peer_response_message = self.recieve_message()
        
        if peer_response_message is None:
            return None

        
        decoded_message = PEER_MESSAGE_DECODER.decode(peer_response_message)
        if decoded_message is None:
            return None

        
        recieved_message_log = 'recieved message <----- ' + decoded_message.__str__() 
        self.peer_logger.log(recieved_message_log)

        
        self.handle_message(decoded_message)
        return decoded_message

    def handle_message(self, decoded_message):
        
        message_handler = self.response_handler[decoded_message.message_id]
        
        return message_handler(decoded_message)

    def recieved_keep_alive(self, keep_alive_message):
         
         self.keep_alive_timer = time.time()

    def recieved_choke(self, choke_message):
        
        self.state.set_peer_choking()
        
        self.state.set_client_not_interested()

    def recieved_unchoke(self, unchoke_message):
        
        self.state.set_peer_unchoking()
        
        self.state.set_client_interested()

    def recieved_interested(self, interested_message):
        
        self.state.set_peer_interested()

    def recieved_uninterested(self, uninterested_message): 
        
        self.state.set_peer_not_interested()
        
        self.close_peer_connection()

    def recieved_bitfield(self, bitfield_message):
        
        self.bitfield_pieces = bitfield_message.extract_pieces()

    def recieved_have(self, have_message):
        
        self.bitfield_pieces.add(have_message.piece_index) 

    def recieved_request(self, request_message):
        
        piece_index     = request_message.piece_index
        block_offset    = request_message.block_offset
        block_length    = request_message.block_length
        
        if self.torrent.validate_piece_length(piece_index, block_offset, block_length):
            
            data_block = self.file_handler.read_block(piece_index, block_offset, block_length)
            
            response_message = piece(piece_index, block_offset, data_block)
            self.send_message(response_message)
        else:
            request_log = self.unique_id + ' dropping request since invalid block requested !' 
            self.peer_logger.log(request_log)

    def recieved_piece(self, piece_message):
        
        self.file_handler.write_block(piece_message) 

    def recieved_cancel(self, cancel_message):
        
        pass

    def recieved_port(self, cancel_message):
        
        pass

    def send_keep_alive(self):
        self.send_message(keep_alive())

    def send_choke(self):
        self.send_message(choke())
        self.state.set_client_choking()

    def send_unchoke(self):
        self.send_message(unchoke())
        self.state.set_client_unchoking()

    def send_interested(self):
        self.send_message(interested())
        self.state.set_client_interested()

    def send_uninterested(self):
        self.send_message(uninterested())
        self.state.set_client_not_interested()

    def send_have(self, piece_index):
        self.send_message(have(piece_index))

    def send_bitfield(self):
        bitfield_payload = create_bitfield_message(self.bitfield_pieces, self.torrent.pieces_count)
        self.send_message(bitfield(bitfield_payload))

    def send_request(self, piece_index, block_offset, block_length):
        self.send_message(request(piece_index, block_offset, block_length))

    def send_piece(self, piece_index, block_offset, block_data):
        self.send_message(piece(piece_index, block_offset, block_data))

    def piece_downlaod_FSM(self, piece_index):
        
        if not self.have_piece(piece_index):
            return False
        
        self.keep_alive_timer = time.time()
        
        download_status = False
        
        exchange_messages = True
        while exchange_messages:
            
            if(self.check_keep_alive_timeout()):
                self.state.set_null()
            
            if(self.state == DSTATE0):
                self.send_interested()
            
            elif(self.state == DSTATE1):
                response_message = self.handle_response()
            
            elif(self.state == DSTATE2):
                download_status = self.download_piece(piece_index)
                exchange_messages = False
            
            elif(self.state == DSTATE3):
                exchange_messages = False
        return download_status

    def download_piece(self, piece_index):
        if not self.have_piece(piece_index) or not self.download_possible():
            return False

        
        recieved_piece = b''  
        
        block_offset = 0
        
        block_length = 0
        
        piece_length = self.torrent.get_piece_length(piece_index)
        
        
        while self.download_possible() and block_offset < piece_length:
            
            if piece_length - block_offset >= self.max_block_length:
                block_length = self.max_block_length
            else:
                block_length = piece_length - block_offset
            
            block_data = self.download_block(piece_index, block_offset, block_length)
            if block_data:
                
                recieved_piece += block_data
                block_offset   += block_length
        
        
        if self.check_keep_alive_timeout():
            return False
        
        
        if(not self.validate_piece(recieved_piece, piece_index)):
            return False
        
        
        download_log  = self.unique_id + ' downloaded piece : '
        download_log += str(piece_index) + ' ' + SUCCESS  
        self.peer_logger.log(download_log)
        
        
        return True

    def download_block(self, piece_index, block_offset, block_length):
        
        request_message = request(piece_index, block_offset, block_length)
        
        self.send_message(request_message)
        
        
        self.torrent.statistics.start_time()
        
        response_message = self.handle_response()
        
        self.torrent.statistics.stop_time()
        
        
        if not response_message or response_message.message_id != PIECE:
            return None
        
        if not self.validate_request_piece_messages(request_message, response_message):
            return None

        
        self.torrent.statistics.update_download_rate(piece_index, block_length)

        
        return response_message.block

    def download_possible(self):
        
        if not self.peer_sock.peer_connection_active():
            return False
        
        if not self.handshake_flag:
            return False
        
        if self.state != DSTATE2:
            return False
        if self.check_keep_alive_timeout():
            return False
        
        return True

    def have_piece(self, piece_index):
        if piece_index in self.bitfield_pieces:
            return True
        else:
            return False

    def add_file_handler(self, file_handler):
        self.file_handler = file_handler

    def validate_request_piece_messages(self, request, piece):
        if request.piece_index != piece.piece_index:
            return False
        if request.block_offset != piece.block_offset:
            return False
        if request.block_length != len(piece.block):
            return False
        return True

    def validate_piece(self, piece, piece_index):
        
        piece_length = self.torrent.get_piece_length(piece_index)
        if (len(piece) != piece_length):
            
            download_log  = self.unique_id + 'unable to downloaded piece ' 
            download_log += str(piece_index) + ' due to validation failure : ' 
            download_log += 'incorrect lenght ' + str(len(piece)) + ' piece recieved '
            download_log += FAILURE
            self.peer_logger.log(download_log)
            return False

        piece_hash = hashlib.sha1(piece).digest()
        index = piece_index * 20
        torrent_piece_hash = self.torrent.torrent_metadata.pieces[index : index + 20]
        
        
        if piece_hash != torrent_piece_hash:
            
            download_log  = self.unique_id + 'unable to downloaded piece ' 
            download_log += str(piece_index) + ' due to validation failure : ' 
            download_log += 'info hash of piece not matched ' + FAILURE
            self.peer_logger.log(download_log)
            return False
        
        return True

    def initial_seeding_messages(self):
        if not self.respond_handshake():
            return False
        
        bitfield = create_bitfield_message(self.bitfield_pieces, self.torrent.pieces_count)
        self.send_message(bitfield)
        return True

    def piece_upload_FSM(self):
        
        self.keep_alive_timer = time.time()
        
        download_status = False
        
        exchange_messages = True
        while exchange_messages:
            
            if(self.check_keep_alive_timeout()):
                self.state.set_null()
            
            if(self.state == USTATE0):
                response_message = self.handle_response()
            
            elif(self.state == USTATE1):
                self.send_unchoke()
            
            elif(self.state == USTATE2):
                self.upload_pieces()
                exchange_messages = False
            
            elif(self.state == USTATE3):
                exchange_messages = False

    def upload_pieces(self):
        while self.upload_possible():
            
            self.torrent.statistics.start_time()
            
            request_message = self.handle_response()
            
            self.torrent.statistics.stop_time()
            if request_message and request_message.message_id == REQUEST:
                piece_index = request_message.piece_index
                block_length = request_message.block_length
                self.torrent.statistics.update_upload_rate(piece_index, block_length)
                self.peer_logger.log(self.torrent.statistics.get_upload_statistics())

    def upload_possible(self):
        
        if not self.peer_sock.peer_connection_active():
            return False
        
        if not self.handshake_flag:
            return False
        
        if self.state != USTATE2:
            return False
        if self.check_keep_alive_timeout():
            return False
        
        return True

    def check_keep_alive_timeout(self):
        if(time.time() - self.keep_alive_timer >= self.keep_alive_timeout):
            keep_alive_log  = self.unique_id + ' peer keep alive timeout ! ' + FAILURE 
            keep_alive_log += ' disconnecting the peer connection!'
            self.close_peer_connection()
            self.peer_logger.log(keep_alive_log)
            return True
        else:
            return False

