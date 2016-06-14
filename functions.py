import socket
import threading


def make_server_socket(port, backlog=5):
    """
    Creates a socket listening for TCP connections in IPv4.

    The socket is set to be reusable immediately.

    :param port: The port to listen
    :type port: int
    :param backlog: The number of connections to queue
    :type backlog: int
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
    print("[%s] %s" % (str(threading.currentThread().getName()), msg))


def send_message(msg, host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    m = bytes(str(msg), 'utf-8')
    sock.sendto(m, (host, int(port)))
