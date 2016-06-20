import socket
import threading
import time
from typing import List
import json

from functions import send_message
from message import Message
from peer import PeerNode

JSON_DATA_PATH = '/Users/gaugendre/Projects/python/botnet-graph/data.json'

peers = []  # type: List[PeerNode]


def update_json(peers_array):
    """
    Updates the data JSON

    :param peers_array: The peers to render in JSON
    :param peers_array: List[PeerNode]
    :rtype: None
    """
    dic = {
        "nodes": [],
        "edges": []
    }

    for peer in peers_array:
        dic['nodes'].append({
            "id": peer.my_id,
            "label": peer.server_port
        })
        for neighbour_id, neighbour in peer.peers.items():
            edge_id = str(peer.server_port) + ':' + str(neighbour['port'])
            dic['edges'].append({
                "id": edge_id,
                "from": peer.my_id,
                "to": neighbour_id
            })

    file = open(JSON_DATA_PATH, 'w')
    with file:
        json.dump(dic, file, indent=2)


def run_update_json(delay):
    while True:
        update_json(peers)
        time.sleep(delay)

if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("www.google.com", 80))
    ip = s.getsockname()[0]
    s.close()

    start_port = 4567
    max_peers = 10
    port_range = range(start_port, start_port + 100)

    t = threading.Thread(target=run_update_json, args=[1])
    t.start()

    for port_number in port_range:
        peer = PeerNode(max_peers, port_number)
        peer.debug = False
        peers.append(peer)
        print('Creating peer ', port_number)

        for peer_port in range(start_port, start_port + max_peers):
            if peer_port != port_number:
                peer.add_peer(ip, peer_port)

        name = ip + ':' + str(port_number)
        t = threading.Thread(target=peer.mainloop, name=name)
        t.start()
        # time.sleep(0.5)

    for peer in peers:
        peer.debug = True

    print('CREATED ALL PEERS')

    time.sleep(4)
    print('STARTING ANOTHER PEER')
    time.sleep(1)

    port_number = 1566
    peer = PeerNode(max_peers, port_number)
    print('Creating peer ', port_number)
    peer.add_peer(ip, 4567)
    peer.add_peer(ip, 4568)
    peers.append(peer)

    name = ip + ':' + str(port_number)
    t = threading.Thread(target=peer.mainloop, name=name)
    t.start()

    m = Message(10, 'GET', ['http://pcksr.net/ptir.php?legit'])
    send_message(m, 'localhost', 1566)
