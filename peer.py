import socket
import threading
import traceback

import time

import math
from typing import Dict, List, Union

import random
from functions import make_server_socket, debug, send_message
from message import Message, MessageNotValidException


class PeerNode:
    def __init__(self, max_peers, server_port, server_host=None) -> None:
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
        self.peers = {}  # type: Dict[str, Dict[str, Union[bool, str, int]]]

        # used to stop the main loop
        self.shutdown = False

        self.handlers = {}
        self.router = None

        self.peer_lock = threading.Lock()

        self.recently_received = []  # type: List[str]

    def __init_server_host(self) -> None:
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

    def __debug(self, msg) -> None:
        """
        Prints a debug message if debug is enabled.

        :param msg: The message to print
        :type msg: str
        :return: Nothing
        :rtype: None
        """
        if self.debug:
            debug(msg)

    def mainloop(self) -> None:
        """
        Initializes the server socket and listen for connections.

        :rtype: None
        """
        s = make_server_socket(self.server_port)  # type: socket.socket
        # s.settimeout(2)
        self.__debug('Server started: {0} ({1}:{2})'.format(self.my_id, self.server_host, self.server_port))

        self.add_handler('PING', self.ping_handler)
        self.add_handler('ALIVE', self.alive_handler)

        self.start_stabilizer(self.check_live_peers, random.randint(3, 10))

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
        :param port: The linked port
        :type sock: socket.socket
        :rtype: None
        """
        self.__debug('New child ' + str(threading.currentThread().getName()))

        try:
            message = Message.from_string(message)
            self.recently_received.append(message.id)
            if not message.is_valid():
                raise MessageNotValidException

            if message.order not in self.handlers:
                self.__debug('Not handled: {0}'.format(str(message)))

            else:
                self.__debug('Handling peer msg: {0}'.format(str(message)))
                self.handlers[message.order](message)
                if not (message.order == 'PING' or message.order == 'ALIVE'):
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
        for peer_id in self.peers:
            peer_id = peer_id.split(':')
            send_message(message, peer_id[0], peer_id[1])

    def __run_stabilizer(self, stabilizer, delay):
        """
        Runs the given function (stabilizer), waits for delay, then repeat until shutdown.

        :param stabilizer: The function to run
        :type stabilizer: function
        :param delay: Amount of time to wait between two calls of stabilizer
        :type delay: int
        :rtype: None
        """
        while not self.shutdown:
            stabilizer()
            time.sleep(delay)

    def start_stabilizer(self, stabilizer, delay):
        """
        Registers and starts a stabilizer function with this peer.
        The function will be activated every <delay> seconds.

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
        if not self.max_peers_reached():
            peer_id = host + ':' + str(port)
            self.peer_lock.acquire()
            self.peers[peer_id] = {
                'alive': True
            }
            self.peer_lock.release()
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
        self.peer_lock.acquire()
        del self.peers[peer_id]
        self.peer_lock.release()

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
        return len(self.peers) < self.max_peers

    def check_live_peers(self):
        """
        Attempts to ping all currently known peers in order to ensure that
        they are still active. Removes any from the peer list that do
        not reply. This function can be used as a simple stabilizer.

        :rtype: None
        """

        to_delete = []

        for peer_id, peer in self.peers.items():
            if peer['alive']:
                peer['alive'] = False
            else:
                to_delete.append(peer_id)

        self.peer_lock.acquire()
        try:
            for peer_id in to_delete:
                del self.peers[peer_id]
        finally:
            self.peer_lock.release()

        m = Message(10, 'PING', [self.server_host, self.server_port])
        self.broadcast_message(m)

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
        self.__debug('Received ' + str(message))
        m = Message(10, 'ALIVE', [self.server_host, self.server_port])
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
        self.__debug('Received ' + str(message))
        peer_id = alive_host + ':' + str(alive_port)
        self.peers[peer_id]['alive'] = True
