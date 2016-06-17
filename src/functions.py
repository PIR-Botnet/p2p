import socket
import threading

from message import Message


def make_server_socket(port):
    """
    Creates a socket listening for TCP connections in IPv4.

    The socket is set to be reusable immediately.

    :param port: The port to listen
    :type port: int
    :return: The created socket
    :rtype: socket.socket
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', port))
    return s


def debug(msg):
    """
    Prints a message to the screen with the name of the current thread

    :param msg: The message to print
    :type msg: str
    :return: Nothing
    :rtype: None
    """
    print("[%s] %s" % (str(threading.currentThread().name), msg))


def send_message(msg, host, port):
    """
    Sends a message to a host:port couple.

    :param msg: The message to send.
    :type msg: Message
    :param host: The ip/host where to send the message.
    :type host: str
    :param port: The port where to send the message.
    :type port: int
    :rtype: None
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    m = bytes(str(msg), 'utf-8')
    sock.sendto(m, (host, int(port)))
