import socket
import threading
from typing import List

import time

from peer import PeerNode

if __name__ == '__main__':
    peers = []  # type: List[PeerNode]

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("www.google.com", 80))
    ip = s.getsockname()[0]
    s.close()

    port_range = range(4567, 4580)

    for port_number in port_range:
        peer = PeerNode(20, port_number)
        peers.append(peer)
        print('Creating peer ', port_number)

        for peer_port in range(4567, 4572):
            if peer_port != port_number:
                peer.add_peer(ip, peer_port)

        t = threading.Thread(target=peer.mainloop)
        t.start()

    print('CREATED ALL PEERS')

    time.sleep(5)
    print('STARTING ANOTHER PEER')
    time.sleep(1)

    port_number = 4591
    peer = PeerNode(20, port_number)
    print('Creating peer ', port_number)
    peer.add_peer(ip, 4567)
    peer.add_peer(ip, 4568)

    t = threading.Thread(target=peer.mainloop)
    t.start()
    time.sleep(1)
    print('\n\nPEERS :')
    print(peer.peers)
