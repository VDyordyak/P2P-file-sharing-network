import sys
import argparse
from client import *

def main(user_arguments):
    client = bittorrent_client(user_arguments)
    client.contact_trackers()
    client.initialize_swarm()
    client.event_loop()

if __name__ == '__main__':
    bittorrent_description  = 'P2P file sharing network'

    parser = argparse.ArgumentParser(description=bittorrent_description)
    parser.add_argument(TORRENT_FILE_PATH, help='unix file path of torrent file')
    parser.add_argument("-d", "--" + DOWNLOAD_DIR_PATH, help="unix directory path of downloading file")
    parser.add_argument("-s", "--" + SEEDING_DIR_PATH, help="unix directory path for the seeding file")
    parser.add_argument("-m", "--" + MAX_PEERS, help="maximum peers participating in upload/download of file")
    parser.add_argument("-l", "--" + RATE_LIMIT, help="upload / download limits in Kbps")
    parser.add_argument("-a", "--" + AWS, action="store_true", default=False, help="test download from AWS Cloud")

    options = vars(parser.parse_args(sys.argv[1:]))
    
    if(options[DOWNLOAD_DIR_PATH] is None and options[SEEDING_DIR_PATH] is None):
        print('KP-Bittorrent works with either download or upload arguments, try using --help')
        sys.exit()
    
    if options[MAX_PEERS] and int(options[MAX_PEERS]) > 50:
        print("P2P file sharing network doesn't support more than 50 peer connection !")
        sys.exit()
    
    if options[RATE_LIMIT] and int(options[RATE_LIMIT]) <= 0:
        print("P2P file sharing network upload / download rate must always greater than 0 Kbps")
        sys.exit()
    
    main(options)


