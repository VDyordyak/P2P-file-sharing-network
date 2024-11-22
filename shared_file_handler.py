import os
from threading import *

class file_io():
    
    def __init__(self, file_path):
        
        self.file_descriptor = os.open(file_path, os.O_RDWR | os.O_CREAT) 

    
    def write(self, byte_stream):
        os.write(self.file_descriptor, byte_stream)   

    
    def read(self, buffer_size):
        byte_stream = os.read(self.file_descriptor, buffer_size)
        return byte_stream
    
    
    def write_null_values(self, data_size):
        
        max_write_buffer = (2 ** 14)
        
        self.move_descriptor_position(0)
        while(data_size > 0):
            if data_size >= max_write_buffer:
                data_size = data_size - max_write_buffer
                data = b'\x00' * max_write_buffer
            else:
                data = b'\x00' * data_size
                data_size = 0
            self.write(data)
        
    
    def move_descriptor_position(self, index_position):
        os.lseek(self.file_descriptor, index_position, os.SEEK_SET)

# TODO : case of multiple torrent files initialization needs to be handled
class torrent_shared_file_handler():
    
    def __init__(self, download_file_path, torrent):
        self.download_file_path = download_file_path
        self.torrent = torrent
        
        self.file_size = torrent.torrent_metadata.file_size
        
        self.piece_size = torrent.torrent_metadata.piece_length
        
        self.download_file = file_io(self.download_file_path)
        
        self.shared_file_lock = Lock()
    
    
    
    def initialize_for_download(self):
        
        self.download_file.write_null_values(self.file_size)
   
    
    def calculate_file_position(self, piece_index, block_offset):
        return piece_index * self.piece_size + block_offset
   

    
    def initalize_file_descriptor(self, piece_index, block_offset):
        
        file_descriptor_position = self.calculate_file_position(piece_index, block_offset)
        
        self.download_file.move_descriptor_position(file_descriptor_position)

    def write_block(self, piece_message):
        
        piece_index     = piece_message.piece_index
        block_offset    = piece_message.block_offset
        data_block      = piece_message.block
        self.shared_file_lock.acquire()
        
        self.initalize_file_descriptor(piece_index, block_offset)
        
        self.download_file.write(data_block)
        self.shared_file_lock.release()

    def read_block(self, piece_index, block_offset, block_size):     
        self.shared_file_lock.acquire()   
        
        self.initalize_file_descriptor(piece_index, block_offset)  
        
        data_block  = self.download_file.read(block_size)
        self.shared_file_lock.release()
        
        return data_block
    


