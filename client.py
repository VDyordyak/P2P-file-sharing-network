import sys
from torrent_file_handler import torrent_file_reader
from tracker import torrent_tracker
from torrent import *
from swarm import swarm
from shared_file_handler import torrent_shared_file_handler
from torrent_logger import *

TORRENT_FILE_PATH = 'torrent_file_path'
DOWNLOAD_DIR_PATH = 'download_directory_path'
SEEDING_DIR_PATH = 'seeding_directory_path'
MAX_PEERS = 'max_peers'
RATE_LIMIT = 'rate_limit'
AWS = 'AWS'

class bittorrent_client():
    def __init__(self, user_arguments):
        torrent_file_path = user_arguments[TORRENT_FILE_PATH]
        self.bittorrent_logger = torrent_logger('P2P file sharing network', BITTORRENT_LOG_FILE, DEBUG)
        self.bittorrent_logger.set_console_logging()
        self.bittorrent_logger.log('Reading ' + torrent_file_path + ' file ...')
        self.torrent_info = torrent_file_reader(torrent_file_path)
        self.client_request = {'seeding': None, 'downloading': None, 'uploading rate': sys.maxsize, 'downloading rate': sys.maxsize, 'max peers': 4, 'AWS': False}
        
        if user_arguments[DOWNLOAD_DIR_PATH]:
            self.client_request['downloading'] = user_arguments[DOWNLOAD_DIR_PATH]
            if user_arguments[RATE_LIMIT]:
                self.client_request['downloading rate'] = int(user_arguments[RATE_LIMIT])
        elif user_arguments[SEEDING_DIR_PATH]:
            self.client_request['seeding'] = user_arguments[SEEDING_DIR_PATH]
            if user_arguments[RATE_LIMIT]:
                self.client_request['uploading rate'] = int(user_arguments[RATE_LIMIT])
        if user_arguments[MAX_PEERS]:
            self.client_request['max peers'] = int(user_arguments[MAX_PEERS])
        if user_arguments[AWS]:
            self.client_request['AWS'] = True
        else:
            self.client_request['AWS'] = False
        
        self.torrent = torrent(self.torrent_info.get_data(), self.client_request)
        self.bittorrent_logger.log(str(self.torrent))

    def contact_trackers(self):
        self.bittorrent_logger.log('Connecting to Trackers ...')
        self.trackers_list = torrent_tracker(self.torrent)
        self.active_tracker = self.trackers_list.request_connection()
        self.bittorrent_logger.log(str(self.active_tracker))

    def initialize_swarm(self):
        self.bittorrent_logger.log('Initializing the swarm of peers ...')
        peers_data = self.active_tracker.get_peers_data()
        if self.client_request['downloading'] is not None:
            self.swarm = swarm(peers_data, self.torrent)
        if self.client_request['seeding'] is not None:
            peers_data['peers'] = []
            self.swarm = swarm(peers_data, self.torrent)

    def seed(self):
        self.bittorrent_logger.log('Client started seeding ...')
        upload_file_path = self.client_request['seeding']
        file_handler = torrent_shared_file_handler(upload_file_path, self.torrent)
        self.swarm.add_shared_file_handler(file_handler)
        self.swarm.seed_file()

    def download(self):
        download_file_path = self.client_request['downloading'] + self.torrent.torrent_metadata.file_name
        self.bittorrent_logger.log('Initializing the file handler for peers in swarm ...')
        file_handler = torrent_shared_file_handler(download_file_path, self.torrent)
        file_handler.initialize_for_download()
        self.swarm.add_shared_file_handler(file_handler)
        self.bittorrent_logger.log('Client started downloading (check torrent statistics) ...')
        self.swarm.download_file()

    def event_loop(self):
        if self.client_request['downloading'] is not None:
            self.download()
        if self.client_request['seeding'] is not None:
            self.seed()
