import uuid


class Message:
    def __init__(self, ttl, order, data=None, msg_id=None):
        """
        Creates a message given an id, a ttl, an order to execute and some data.

        :param ttl: The TTL of the message. Will be decremented each time a peer broadcasts it.
        :type ttl: int
        :param order: The order to execute.
        :type order: str
        :param data: The data for the order.
        :type data: list(str)
        """
        self.id = msg_id or str(uuid.uuid4())
        self.ttl = ttl
        self.order = order.upper()
        self.data = data

    def __str__(self):
        """
        Returns the string representation of the message in order to send it.

        :return: The string representation of the message
        :rtype: str
        """
        message = '{id};{ttl};{order};'.format(id=self.id, ttl=self.ttl, order=self.order)
        for index, d in enumerate(self.data):
            if index > 0:
                message += ','
            message += str(d)
        return message

    @classmethod
    def from_string(cls, str_rep):
        """
        Creates a message given its string representation.

        :param str_rep: The string representation of the message
        :type str_rep: str
        :return: The newly created message
        :rtype: Message
        """
        count = str_rep.count(';')
        data = None

        if count == 2:
            uid, ttl, order = str_rep.split(';')
        elif count == 3:
            uid, ttl, order, data = str_rep.split(';')
        else:
            uid = 0
            ttl = 0
            order = ''

        ttl = int(ttl)
        if data is not None:
            data = data.split(',')
        return cls(ttl, order.upper(), data, msg_id=uid)

    def is_valid(self):
        """
        Tells if the message is valid.

        A message is valid if it has a not empty order.

        :return: True if the message is valid, False otherwise.
        :rtype: bool
        """
        return self.order is not None and self.order != ''

    def is_expired(self):
        """
        Tells if the message is expired.

        A message is expired when its ttl is less than or equal to 0.

        :return: True if the message is expired, False otherwise.
        :rtype: bool
        """
        return self.ttl <= 0


class MessageNotValidException(Exception):
    pass
