import hashlib
import random as rd

from torrent_statistics import *
from beautifultable import BeautifulTable

class torrent():

    def __init__(self, torrent_metadata, client_request):
        
        self.torrent_metadata   = torrent_metadata
        self.client_request     = client_request

        
        
        self.client_port = 6881
        self.client_IP = ''
            
        
        self.statistics = torrent_statistics(self.torrent_metadata)
            
        
        self.block_length   = 16 * (2 ** 10) 
        
        
        self.piece_length = torrent_metadata.piece_length

        
        if self.client_request['seeding'] != None:
            self.statistics.num_pieces_downloaded = self.torrent_metadata.file_size

        
        self.pieces_count = int(len(self.torrent_metadata.pieces) / 20)

        
        self.peer_id = ('-PC0001-' + ''.join([str(rd.randint(0, 9)) for i in range(12)])).encode()
    
    
    
    def get_piece_length(self, piece_index):
        
        if piece_index == self.pieces_count - 1:
            return self.torrent_metadata.file_size - self.torrent_metadata.piece_length * (piece_index)
        else:
            return self.torrent_metadata.piece_length
  
    
    def validate_piece_length(self, piece_index, block_offset, block_length):
        if block_length > self.block_length:
            return False
        elif block_length + block_offset > self.get_piece_length(piece_index):
            return False
        return True
        
    
    def __str__(self):
        column_header =  'CLIENT TORRENT DATA (client state = '
        if self.client_request['downloading'] != None:
            column_header += 'downloading)'
        if self.client_request['seeding'] != None:
            column_header += 'seeding)'
        
        torrent_file_table = BeautifulTable()
        torrent_file_table.columns.header = [column_header, "DATA VALUE"]
        
        
        torrent_file_table.rows.append(['File name', str(self.torrent_metadata.file_name)])
        
        torrent_file_table.rows.append(['File size', str(round(self.torrent_metadata.file_size / (2 ** 20), 2)) + ' MB'])
        
        torrent_file_table.rows.append(['Piece length', str(self.torrent_metadata.piece_length)])
        
        torrent_file_table.rows.append(['Info hash', '20 Bytes file info hash value'])
        
        if self.torrent_metadata.files:
            torrent_file_table.rows.append(['Files', str(len(self.torrent_metadata.files))])
        else:
            torrent_file_table.rows.append(['Files', str(self.torrent_metadata.files)])
        
        torrent_file_table.rows.append(['Number of Pieces', str(self.pieces_count)])
        
        torrent_file_table.rows.append(['Client port', str(self.client_port)])
        torrent_file_table.rows.append(['Client peer ID', str(self.peer_id)])
        
        return str(torrent_file_table)


