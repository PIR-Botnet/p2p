import socket
import threading
import time
from typing import List
import json

from peer import PeerNode

JSON_DATA_PATH = '/home/gaugendre/Projects/python/graph-botnet/data.json'

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
    json.dump(dic, file)
    print('dumped in JSON')


def run_update_json(delay):
    while True:
        update_json(peers)
        time.sleep(delay)

if __name__ == '__main__':
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

        name = ip + ':' + str(port_number)
        t = threading.Thread(target=peer.mainloop, name=name)
        t.start()

    print('CREATED ALL PEERS')

    t = threading.Thread(target=run_update_json, args=[1])
    t.start()

    time.sleep(4)
    print('STARTING ANOTHER PEER')
    time.sleep(1)

    port_number = 4591
    peer = PeerNode(20, port_number)
    print('Creating peer ', port_number)
    peer.add_peer(ip, 4567)
    peer.add_peer(ip, 4568)
    peers.append(peer)

    name = ip + ':' + str(port_number)
    t = threading.Thread(target=peer.mainloop, name=name)
    t.start()
