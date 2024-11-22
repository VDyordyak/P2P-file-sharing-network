import struct
from torrent_error import *

KEEP_ALIVE      = None
CHOKE           = 0
UNCHOKE         = 1 
INTERESTED      = 2
UNINTERESTED    = 3
HAVE            = 4
BITFIELD        = 5
REQUEST         = 6
PIECE           = 7
CANCEL          = 8
PORT            = 9
HANDSHAKE_MESSAGE_LENGTH = 68
MESSAGE_LENGTH_SIZE     = 4
MESSAGE_ID_SIZE         = 1

class peer_wire_message():

    def __init__(self, message_length, message_id, payload):
        self.message_length = message_length
        self.message_id     = message_id 
        self.payload        = payload

    def message(self):
        
        message  = struct.pack("!I", self.message_length)
        
        if self.message_id != None:
            message += struct.pack("!B", self.message_id)
        
        if self.payload != None:
            message += self.payload
        return message

    def __str__(self):
        message  = 'PEER WIRE MESSAGE : '
        message += '(message length : ' +  str(self.message_length) + '), '
        if self.message_id is None:
            message += '(message id : None), '
        else:
            message += '(message id : ' +  str(self.message_id)       + '), '
        if self.payload is None:
            message += '(protocol length : None)'
        else:
            message += '(payload length : ' +  str(len(self.payload)) + ')'
        return message

class handshake():
    def __init__(self, info_hash, client_peer_id): 
        
        self.protocol_name = "BitTorrent protocol"
        
        self.info_hash = info_hash
        
        self.client_peer_id = client_peer_id

    def message(self):
        handshake_message  = struct.pack("!B", len(self.protocol_name))
        handshake_message += struct.pack("!19s", self.protocol_name.encode())
        handshake_message += struct.pack("!Q", 0x0)
        handshake_message += struct.pack("!20s", self.info_hash)
        handshake_message += struct.pack("!20s", self.client_peer_id)
        return handshake_message

    def validate_handshake(self, response_handshake):
        response_handshake_length = len(response_handshake)
        if(response_handshake_length != HANDSHAKE_MESSAGE_LENGTH):
            err_msg = 'invalid handshake length ( ' + str(response_handshake_length) + 'B )'
            torrent_error(err_msg)
        
        
        peer_info_hash  = response_handshake[28:48]
        
        peer_id         = response_handshake[48:68]

        
        if(peer_info_hash != self.info_hash):
            err_msg = 'info hash with peer of torrnet do not match !'
            torrent_error(err_msg)
        
        if(peer_id == self.client_peer_id):
            err_msg = 'peer ID and client ID both match drop connection !'
            torrent_error(err_msg)

        
        return handshake(peer_info_hash, peer_id)

class keep_alive(peer_wire_message):
    def __init__(self):   
        message_length  = 0                                 
        message_id      = KEEP_ALIVE                        
        payload         = None                              
        super().__init__(message_length, message_id, payload)
    
    def __str__(self):
        message  = 'KEEP ALIVE : '
        message += '(message length : ' + str(self.message_length) + '), '
        message += '(message id : None), '
        message += '(message paylaod : None)'
        return message

class choke(peer_wire_message):
    def __init__(self):   
        message_length = 1                                  
        message_id     = CHOKE                              
        payload        = None                               
        super().__init__(message_length, message_id, payload)

    def __str__(self):
        message  = 'CHOKE : '
        message += '(message length : ' + str(self.message_length)  + '), '
        message += '(message id : '     + str(self.message_id)      + '), '
        message += '(message paylaod : None)'
        return message

class unchoke(peer_wire_message):
    def __init__(self):   
        message_length = 1                                  
        message_id     = UNCHOKE                            
        payload        = None                               
        super().__init__(message_length, message_id, payload)

    def __str__(self):
        message  = 'UNCHOKE : '
        message += '(message length : ' + str(self.message_length)  + '), '
        message += '(message id : '     + str(self.message_id)      + '), '
        message += '(message paylaod : None)'
        return message

class interested(peer_wire_message):
    def __init__(self):   
        message_length = 1                                  
        message_id     = INTERESTED                         
        payload        = None                               
        super().__init__(message_length, message_id, payload)

    def __str__(self):
        message  = 'INTERESTED : '
        message += '(message length : ' + str(self.message_length)  + '), '
        message += '(message id : '     + str(self.message_id)      + '), '
        message += '(message paylaod : None)'
        return message

class uninterested(peer_wire_message):
    def __init__(self):   
        message_length = 1                                  
        message_id     = UNINTERESTED                       
        payload        = None                               
        super().__init__(message_length, message_id, payload)

    def __str__(self):
        message  = 'UNINTERESTED : '
        message += '(message length : ' + str(self.message_length)  + '), '
        message += '(message id : '     + str(self.message_id)      + '), '
        message += '(message paylaod : None)'
        return message

class have(peer_wire_message):
    def __init__(self, piece_index):   
        message_length = 5                                  
        message_id     = HAVE                               
        payload        = struct.pack("!I", piece_index)     
        super().__init__(message_length, message_id, payload)
        
        self.piece_index = piece_index

    def __str__(self):
        message  = 'HAVE : '
        message += '(message length : ' + str(self.message_length)  + '), '
        message += '(message id : '     + str(self.message_id)      + '), '
        message += '(message paylaod : [piece index : ' + str(self.piece_index) + '])'
        return message

class bitfield(peer_wire_message):
    def __init__(self, pieces_info):
        message_length  = 1 + len(pieces_info)              
        message_id      = BITFIELD                          
        payload         = pieces_info                       
        super().__init__(message_length, message_id, payload)
        
        self.pieces_info = pieces_info

    def extract_pieces(self):
        bitfield_pieces = set([])
        
        for i, byte_value in enumerate(self.payload):
            for j in range(8):
                
                if((byte_value >> j) & 1):
                    piece_number = i * 8 + 7 - j
                    bitfield_pieces.add(piece_number)
        
        return bitfield_pieces

    def __str__(self):
        message  = 'BITFIELD : '
        message += '(message paylaod : [bitfield length : ' + str(len(self.pieces_info)) + '])'
        return message

class request(peer_wire_message):
    def __init__(self, piece_index, block_offset, block_length):
        message_length  = 13                                
        message_id      = REQUEST                           
        payload         = struct.pack("!I", piece_index)    
        payload        += struct.pack("!I", block_offset) 
        payload        += struct.pack("!I", block_length) 
        super().__init__(message_length, message_id, payload)
        
        self.piece_index    = piece_index
        self.block_offset   = block_offset
        self.block_length   = block_length  

    def __str__(self):
        message  = 'REQUEST : '
        message += '(message paylaod : [ '
        message += 'piece index : '     + str(self.piece_index)     + ', '
        message += 'block offest : '    + str(self.block_offset)    + ', '
        message += 'block length : '    + str(self.block_length)    + ' ])'
        return message

class piece(peer_wire_message):
    
    def __init__(self, piece_index, block_offset, block):
        message_length  = 9 + len(block)                    
        message_id      = PIECE                             
        payload         = struct.pack("!I", piece_index)    
        payload        += struct.pack("!I", block_offset)
        payload        += block
        super().__init__(message_length, message_id, payload)
        self.piece_index    = piece_index
        self.block_offset   = block_offset
        self.block          = block 

    def __str__(self):
        message  = 'PIECE : '
        message += '(message paylaod : [ '
        message += 'piece index : '     + str(self.piece_index)     + ', '
        message += 'block offest : '    + str(self.block_offset)    + ', '
        message += 'block length : '    + str(len(self.block))      + ' ])'
        return message

def create_bitfield_message(bitfield_pieces, total_pieces):
    bitfield_payload = b''
    piece_byte = 0
    for i in range(total_pieces):
        if i in bitfield_pieces:
            piece_byte = piece_byte | (2 ** 8)
            piece_byte = piece_byte >> 1
        if (i + 1) % 8 == 0:
            bitfield_payload += struct.pack("!B", piece_byte)
            piece_byte = 0
    if total_pieces % 8 != 0:
        bitfield_payload += struct.pack("!B", piece_byte)
    return bitfield(bitfield_payload)

class peer_message_decoder():
    def decode(self, peer_message):
        if peer_message.message_id == KEEP_ALIVE :
            self.peer_decoded_message = keep_alive()
        elif peer_message.message_id == CHOKE :    
            self.peer_decoded_message = choke()
        elif peer_message.message_id == UNCHOKE :        
            self.peer_decoded_message = unchoke()
        elif peer_message.message_id == INTERESTED :     
            self.peer_decoded_message = interested()
        elif peer_message.message_id == UNINTERESTED :
            self.peer_decoded_message = uninterested()
        elif peer_message.message_id == HAVE :
            piece_index = struct.unpack_from("!I", peer_message.payload)[0]
            self.peer_decoded_message = have(piece_index)
        elif peer_message.message_id == BITFIELD :
            self.peer_decoded_message = bitfield(peer_message.payload)
        elif peer_message.message_id == REQUEST :        
            piece_index  = struct.unpack_from("!I", peer_message.payload, 0)[0]
            block_offset = struct.unpack_from("!I", peer_message.payload, 4)[0]
            block_length = struct.unpack_from("!I", peer_message.payload, 8)[0]
            self.peer_decoded_message = request(piece_index, block_offset, block_length)
        elif peer_message.message_id == PIECE :          
            piece_index  = struct.unpack_from("!I", peer_message.payload, 0)[0]
            begin_offset = struct.unpack_from("!I", peer_message.payload, 4)[0]
            block = peer_message.payload[8:]
            self.peer_decoded_message = piece(piece_index, begin_offset, block)
        elif peer_message.message_id == CANCEL :          
            self.peer_decoded_message = None

        elif peer_message.message_id == PORT :           
            self.peer_decoded_message = None
        else:
            self.peer_decoded_message = None
        return self.peer_decoded_message

PEER_MESSAGE_DECODER = peer_message_decoder()