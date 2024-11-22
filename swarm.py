import sys
import time
import random
from copy import deepcopy
from datetime import timedelta
from threading import *
from peer import peer
from torrent_error import *
from torrent_logger import *

class swarm():

    def __init__(self, peers_data, torrent):
        
        self.torrent    = deepcopy(torrent)
        self.interval   = peers_data['interval']
        self.seeders    = peers_data['seeders']
        self.leechers   = peers_data['leechers']
    
        
        self.peers_list = []
        
        if self.torrent.client_request['AWS']:
            self.peers_list.append(peer('34.238.166.126', 6881, torrent))

        for peer_IP, peer_port in peers_data['peers']:
            self.peers_list.append(peer(peer_IP, peer_port, torrent))
        
        
        self.bitfield_pieces_count = dict()

        
        self.top_n = self.torrent.client_request['max peers']

        
        self.swarm_logger = torrent_logger('swarm', SWARM_LOG_FILE, DEBUG)
        
        self.torrent_stats_logger = torrent_logger('torrent_statistics', TORRENT_STATS_LOG_FILE, DEBUG)
        self.torrent_stats_logger.set_console_logging()

        
        self.bitfield_pieces_downloaded = set([])
                
        
        self.file_handler = None
    
        
        self.minimum_pieces = 10

        
        if torrent.client_request['seeding'] != None:
            
            self.client_peer = peer(self.torrent.client_IP, self.torrent.client_port, self.torrent)
            self.client_peer.initialize_seeding()
        
        
        self.swarm_lock = Lock()

    def update_bitfield_count(self, bitfield_pieces):
        for piece in bitfield_pieces:
            if piece in self.bitfield_pieces_count.keys():
                self.bitfield_pieces_count[piece] += 1
            else:
                self.bitfield_pieces_count[piece] = 1

    def add_shared_file_handler(self, file_handler):
        
        self.file_handler = file_handler
        for peer in self.peers_list:
            peer.add_file_handler(self.file_handler)

    def have_file_handler(self):
        if self.file_handler is None:
            download_log  = 'Cannot download file : '
            download_log += ' file handler not instantiated ! ' + FAILURE
            self.swarm_logger.log(download_log)
            return False
        return True

    def connect_to_peer(self, peer_index):
        
        self.peers_list[peer_index].initiate_handshake()
        
        peer_bitfield_pieces = self.peers_list[peer_index].initialize_bitfield()
        self.swarm_lock.acquire()
        
        self.update_bitfield_count(peer_bitfield_pieces) 
        self.swarm_lock.release()
        
        self.swarm_logger.log(self.peers_list[peer_index].get_handshake_log())

    def have_active_connections(self):
        for peer in self.peers_list:
            if peer.peer_sock.peer_connection_active():
                return True
        return False

    def download_complete(self):
        return len(self.bitfield_pieces_downloaded) == self.torrent.pieces_count

    def download_file(self):
        
        if not self.have_file_handler():
            return False
        
        for peer_index in range(len(self.peers_list)):
            connect_peer_thread = Thread(target = self.connect_to_peer, args=(peer_index, ))
            connect_peer_thread.start()
        
        download_thread = Thread(target = self.download_using_stratergies)
        download_thread.start()

    def download_using_stratergies(self):
        self.download_start_time = time.time()
        while not self.download_complete():
            
            pieces = self.piece_selection_startergy()
            peer_indices = self.peer_selection_startergy()

            
            downloading_thread_pool = []
            for i in range(min(len(pieces), len(peer_indices))):
                piece = pieces[i]
                peer_index = peer_indices[i]
                downloading_thread = Thread(target=self.download_piece, args=(piece, peer_index, ))
                downloading_thread_pool.append(downloading_thread)
                downloading_thread.start()
            
            for downloading_thread in downloading_thread_pool:
                downloading_thread.join()
        self.download_end_time = time.time()
        
        
        download_log  = 'Downloading time: '
        download_log += str(timedelta(seconds=(self.download_end_time - self.download_start_time))).split('.')[0] + ' seconds \n'
        download_log += 'Average download rate: ' 
        download_log += str(self.torrent.statistics.avg_download_rate) + ' Mbps\n'
        self.torrent_stats_logger.log(download_log)

    def download_piece(self, piece, peer_index):
        start_time = time.time()
        is_piece_downloaded = self.peers_list[peer_index].piece_downlaod_FSM(piece)
        end_time = time.time()
        if is_piece_downloaded:
            
            self.swarm_lock.acquire() 
            
            self.bitfield_pieces_downloaded.add(piece)
            
            del self.bitfield_pieces_count[piece]
            
            self.torrent.statistics.update_start_time(start_time)
            self.torrent.statistics.update_end_time(end_time)
            self.torrent.statistics.update_download_rate(piece, self.torrent.piece_length)
            self.torrent_stats_logger.log(self.torrent.statistics.get_download_statistics())
            
            self.swarm_lock.release() 

    def piece_selection_startergy(self):
        return self.rarest_pieces_first()

    def rarest_pieces_first(self):
        
        while(len(self.bitfield_pieces_count) == 0):
            time.sleep(5)
        
        rarest_piece_count = min(self.bitfield_pieces_count.values())
        
        rarest_pieces = [piece for piece in self.bitfield_pieces_count if 
                         self.bitfield_pieces_count[piece] == rarest_piece_count] 
        
        random.shuffle(rarest_pieces)
        
        return rarest_pieces[:self.top_n]

    def peer_selection_startergy(self):
        
        if self.torrent.client_request['AWS']:
            return [self.select_specific_peer()]
        
        if len(self.bitfield_pieces_downloaded) < self.minimum_pieces:
            return self.select_random_peers()
        
        else:
            return self.top_peers()

    def select_random_peers(self):
        peer_indices = []
        
        for index in range(len(self.peers_list)):
            if len(self.peers_list[index].bitfield_pieces) != 0:
                peer_indices.append(index)
        random.shuffle(peer_indices)
        return peer_indices[:self.top_n]

    def select_specific_peer(self):
        peer_index = 0
        return peer_index

    def top_peers(self):
        
        self.peers_list = sorted(self.peers_list, key=self.peer_comparator, reverse=True)
        
        return [peer_index for peer_index in range(self.top_n)]

    def peer_comparator(self, peer):
        if not peer.peer_sock.peer_connection_active():
            return -sys.maxsize
        return peer.torrent.statistics.avg_download_rate

    def seed_file(self):
        seeding_log = 'Seeding started by client at ' + self.client_peer.unique_id
        self.swarm_logger.log(seeding_log)
        seeding_file_forever = True
        while seeding_file_forever:
            recieved_connection = self.client_peer.recieve_connection()
            if recieved_connection != None:
                
                peer_socket, peer_address = recieved_connection
                peer_IP, peer_port = peer_address
                
                peer_object = peer(peer_IP, peer_port, self.torrent, peer_socket)
                peer_object.set_bitfield() 
                peer_object.add_file_handler(self.file_handler)
                
                Thread(target = self.upload_file, args=(peer_object,)).start()
            else:
                time.sleep(1)

    def upload_file(self, peer):
        
        if not peer.initial_seeding_messages():
            return 
        
        peer.piece_upload_FSM()


