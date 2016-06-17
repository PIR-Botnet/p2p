import math
import socket
import threading
import time
import traceback
from datetime import datetime
from typing import Dict, Union, List

from message import Message, MessageNotValidException

import random
from operator import itemgetter
from functions import make_server_socket, debug, send_message

PERCENTAGE_OF_OLDEST_TO_REMOVE = 0.2


class PeerNode:
    def __init__(self, max_peers, server_port, server_host=None):
        """
        Initialize the PeerNode

        :param max_peers: The maximum number of peers. Can be set to 0 to allow
        an unlimited number of peers.
        :type max_peers: int
        :param server_port: The port to listen to.
        :type server_port: int
        :param server_host: The host address. If not supplied, will be
        determined by trying to connect to google.com.
        :type server_host: str
        :rtype: None
        """
        self.debug = True

        self.max_peers = int(max_peers)
        if self.max_peers < 0:
            self.max_peers = math.inf

        self.server_port = int(server_port)

        # If not supplied, the host name/IP address will be determined
        # by attempting to connect to an Internet host like Google.
        if server_host:
            self.server_host = str(server_host)
        else:
            self.__init_server_host()

        # Id composed of hostname and port
        self.my_id = '{0}:{1}'.format(self.server_host, self.server_port)

        # list of known peers
        self.peers = {}  # type: Dict[str, Dict[str, Union[bool, str, int, datetime]]]

        # used to stop the main loop
        self.shutdown = False

        self.handlers = {}
        self.router = None

        self.peer_lock = threading.Lock()

        self.recently_received = {}  # type: Dict[str, datetime]

        self.recent_timeout = 300

    def __init_server_host(self):
        """
        Determines the local machine's IP address.

        Attempts to connect to an Internet host in order to determine
        the local machine's IP address.

        :return: Nothing
        :rtype: None
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("www.google.com", 80))
        self.server_host = s.getsockname()[0]
        s.close()

    def __debug(self, msg):
        """
        Prints a debug message if debug is enabled.

        :param msg: The message to print
        :type msg: str
        :return: Nothing
        :rtype: None
        """
        if self.debug:
            debug(msg)

    def mainloop(self):
        """
        Initializes the server socket and listen for connections.

        :rtype: None
        """
        s = make_server_socket(self.server_port)  # type: socket.socket
        self.__debug('Server started: {0} ({1}:{2})'.format(self.my_id, self.server_host, self.server_port))

        self.add_handler('PING', self.ping_handler)
        self.add_handler('ALIVE', self.alive_handler)
        self.add_handler('HELLO', self.hello_handler)
        self.add_handler('PEERS', self.peers_handler)

        hello_msg = Message(1, 'HELLO', [self.server_host, self.server_port])
        self.broadcast_message(hello_msg)

        self.start_stabilizer(self.check_live_peers, random.randint(3, 10) * 60)
        self.start_stabilizer(self.clear_old_messages, 45)

        while not self.shutdown:
            try:
                (message, (host, port)) = s.recvfrom(4096)
                message = message.decode('utf-8')
                self.__debug('Received ' + str(message))

                t = threading.Thread(target=self.__handle_peer, args=[message, host, port, s])
                t.start()
            except KeyboardInterrupt:
                self.shutdown = True
                continue
            except:
                if self.debug:
                    traceback.print_exc()
                    continue

        self.__debug('Main loop exiting')

    def __handle_peer(self, message, host, port, sock):
        """
        Handles a received message

        :param message: The received message
        :type message: str
        :param host: The address from which the message was received
        :type host: str
        :param port: The linked port
        :type port: int
        :type sock: socket.socket
        :rtype: None
        """
        self.__debug('New child ' + str(threading.currentThread().getName()))

        try:
            message = Message.from_string(message)

            if message.id in self.recently_received:
                return
            self.recently_received[message.id] = datetime.now()

            if not message.is_valid():
                raise MessageNotValidException

            if message.order not in self.handlers:
                self.__debug('Not handled: {0}'.format(str(message)))

            else:
                self.__debug('Handling peer msg: {0}'.format(str(message)))
                self.handlers[message.order](message)
                message.ttl -= 1
                if message.ttl > 0:
                    self.broadcast_message(message)

        except KeyboardInterrupt:
            raise

        except:
            if self.debug:
                traceback.print_exc()

    def broadcast_message(self, message):
        """
        Sends a message to all peers

        :param message: The message to send
        :type message: Message
        :rtype: None
        """
        with self.peer_lock:
            for peer_id in self.peers:
                peer_id = peer_id.split(':')
                send_message(message, peer_id[0], int(peer_id[1]))

    def __run_stabilizer(self, stabilizer, delay):
        """
        Runs the given function (stabilizer), waits for <delay> minutes, then repeat until shutdown.

        :param stabilizer: The function to run
        :type stabilizer: function
        :param delay: Amount of time in seconds to wait between two calls of stabilizer
        :type delay: int
        :rtype: None
        """
        while not self.shutdown:
            stabilizer()
            time.sleep(delay)

    def start_stabilizer(self, stabilizer, delay):
        """
        Registers and starts a stabilizer function with this peer.

        The function will be activated every <delay> minutes.

        :param stabilizer: The function to run
        :type stabilizer: function
        :param delay: Amount of time in seconds to wait between two calls of stabilizer
        :type delay: int
        :rtype: None
        """
        t = threading.Thread(target=self.__run_stabilizer,
                             args=[stabilizer, delay])
        t.start()

    def add_handler(self, order, handler):
        """
        Registers the handler for the given message type with this peer.

        :param order: The order against which to check
        :type order: str
        :param handler: The function to run when receiving order
        :type handler: function
        :rtype: None
        """
        self.handlers[order] = handler

    def add_peer(self, host, port):
        """
        Adds a peer name and host:port mapping to the known list of peers.

        :param host: The host to add
        :type host: str
        :param port: The linked port
        :type port: int
        :rtype: None
        """
        host = str(host)
        port = int(port)
        if host == self.server_host and port == self.server_port:
            return
        if not self.max_peers_reached():
            self.__debug('Adding peer ' + str(port))
            peer_id = host + ':' + str(port)
            with self.peer_lock:
                self.peers[peer_id] = {
                    'alive': True,
                    'time_added': datetime.now(),
                    'host': host,
                    'port': port
                }
        else:
            self.__debug("Can't add new peer : max reached.")

    def remove_peer(self, host, port):
        """
        Removes peer information from the known list of peers.

        :param host: The host to remove
        :type host: str
        :param port: The linked port
        :type port: int
        :rtype: None
        """
        peer_id = host + ':' + str(port)
        with self.peer_lock:
            del self.peers[peer_id]

    def number_of_peers(self):
        """
        Return the number of known peer's.

        :return: The current number of peers
        :rtype: int
        """
        return len(self.peers)

    def max_peers_reached(self):
        """
        Returns whether the maximum limit of names has been added to the
        list of known peers. Always returns True if maxpeers is set to 0.

        :return: Maximum of peers reached ?
        :rtype: bool
        """
        return len(self.peers) >= self.max_peers

    def check_live_peers(self):
        """
        Attempts to ping all currently known peers in order to ensure that
        they are still active. Removes any from the peer list that do
        not reply. This function can be used as a simple stabilizer.

        :rtype: None
        """

        to_delete = set()

        with self.peer_lock:
            for peer_id, peer in self.peers.items():
                if peer['alive']:
                    peer['alive'] = False
                else:
                    to_delete.add(peer_id)

            if len(self.peers) > 0.8 * self.max_peers:
                sorted_peers = self.get_sorted_peers()
                if sorted_peers is not None:
                    for i in range(int(PERCENTAGE_OF_OLDEST_TO_REMOVE * len(self.peers))):
                        peer = sorted_peers[i]
                        peer_id = peer['host'] + ':' + str(peer['port'])
                        to_delete.add(peer_id)

            for peer_id in to_delete:
                del self.peers[peer_id]

        m = Message(1, 'PING', [self.server_host, self.server_port])
        self.broadcast_message(m)

    def get_sorted_peers(self):
        with self.peer_lock:
            sorted_peers = sorted(self.peers.values(), key=itemgetter('time_added'))
        return sorted_peers

    def ping_handler(self, message):
        """
        Handles a PING message.

        Responds with an ALIVE message.

        :param message: The received message.
        :type message: Message
        :rtype: None
        """
        dst_host = message.data[0]
        dst_port = message.data[1]
        m = Message(1, 'ALIVE', [self.server_host, self.server_port])
        send_message(m, dst_host, dst_port)

    def alive_handler(self, message):
        """
        Handles an ALIVE message.

        Switches the alive flag of the peer that sends the ALIVE message to True.

        :param message: The received message
        :type message: Message
        :rtype: None
        """
        alive_host = message.data[0]
        alive_port = message.data[1]
        peer_id = alive_host + ':' + alive_port
        with self.peer_lock:
            self.peers[peer_id]['alive'] = True

    def hello_handler(self, message):
        """
        Handles a HELLO message.

        Adds the peer to the peer list if enough room.
        Sends it back our peer list.

        :param message: The received message.
        :type message: Message
        :rtype: None
        """
        new_host = message.data[0]
        new_port = int(message.data[1])

        if self.max_peers_reached():
            sorted_peers = self.get_sorted_peers()
            if sorted_peers is not None:
                first_peer = sorted_peers[0]
                self.remove_peer(first_peer['host'], first_peer['port'])

        self.add_peer(new_host, new_port)
        with self.peer_lock:
            m = Message(1, 'PEERS', list(self.peers.keys()))
        send_message(m, new_host, new_port)

    def peers_handler(self, message):
        """
        Handles a PEERS message.

        Add all the peers to the current peers list if enough room.

        :param message: The received message.
        :type message: Message
        :rtype: None
        """
        for peer_id in message.data:
            host, port = peer_id.split(':')
            self.add_peer(host, port)

    def clear_old_messages(self):
        """
        Clears the old ids from recently seen messages.

        See also __is_recent(self, received_time).

        :rtype: None
        """
        to_delete = []  # type: List[str]
        for msg_id, received_time in self.recently_received.items():
            if not self.__is_recent(received_time):
                to_delete.append(msg_id)

        for msg_id in to_delete:
            del self.recently_received[msg_id]

    def __is_recent(self, received_time):
        """
        Tells if a time is recent according to the setting in constructor.

        Recent means that the time delta between now and the received time
        is less or equal to the `recent_timeout` in the constructor.

        :param received_time: The time to tell if recent or not.
        :type received_time: datetime
        :return: True if the time is recent, false otherwise
        :rtype: bool
        """
        return (datetime.now() - received_time).seconds <= self.recent_timeout
