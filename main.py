import socket
import threading
from typing import List

from peer import PeerNode

if __name__ == '__main__':
    peers = []  # type: List[PeerNode]

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("www.google.com", 80))
    ip = s.getsockname()[0]
    s.close()

    port_range = range(4567, 4580)

    for port_number in port_range:
        peer = PeerNode(50, port_number)
        peers.append(peer)

        for peer_port in port_range:
            if peer_port != port_number:
                peer.add_peer(ip, peer_port)

        t = threading.Thread(target=peer.mainloop)
        t.start()

