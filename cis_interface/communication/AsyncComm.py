import sys
import uuid
import logging
import threading
from subprocess import Popen, PIPE
from cis_interface import platform, tools
from cis_interface.communication import CommBase


class AsyncTryAgain(Exception):
    r"""Exception raised when comm open, but send should be attempted again."""
    pass


class AsyncComm(CommBase.CommBase):
    r"""Class for handling asynchronous I/O.

    Args:
        name (str): The name of the message queue.
        **kwargs: Additional keyword arguments are passed to CommBase.
        
    Attributes:
        backlog_thread (tools.CisThread): Thread that will handle sending
            or receiving backlogged messages.
        backlog_send_ready (threading.Event): Event set when there is a
            message in the send backlog.
        backlog_recv_ready (threading.Event): Event set when there is a
            message in the recv backlog.
        
    """
    def __init__(self, name, **kwargs):
        self._backlog_recv = []
        self._backlog_send = []
        self._backlog_thread = None
        self.backlog_send_ready = threading.Event()
        self.backlog_recv_ready = threading.Event()
        self.backlog_open = False
        super(AsyncComm, self).__init__(name, **kwargs)

    @property
    def backlog_thread(self):
        r"""tools.CisThread: Thread that will handle sinding or receiving
        backlogged messages."""
        if self._backlog_thread is None:
            if self.direction == 'send':
                self._backlog_thread = CommBase.CommThreadLoop(
                    self, target=self.run_backlog_send, suffix='SendBacklog')
            else:
                self._backlog_thread = CommBase.CommThreadLoop(
                    self, target=self.run_backlog_recv, suffix='RecvBacklog')
        return self._backlog_thread

    def open(self):
        r"""Open the connection by connecting to the queue."""
        super(AsyncComm, self).open()
        self._open_direct()
        self._open_backlog()

    def _open_direct(self):
        r"""Open the comm directly."""
        pass

    def _open_backlog(self):
        r"""Open the backlog."""
        if not self.is_open_backlog:
            self.backlog_open = True
            self.backlog_thread.start()

    def _close_direct(self):
        r"""Close the comm directly."""
        pass

    def _close_backlog(self, wait=False):
        r"""Close the backlog thread."""
        self.backlog_open = False
        self.backlog_thread.set_break_flag()
        self.backlog_send_ready.set()
        self.backlog_recv_ready.set()
        if wait:
            self.backlog_thread.wait(key=str(uuid.uuid4()))

    def _close(self, linger=False):
        r"""Close the connection.

        Args:
            linger (bool, optional): If True, drain messages before closing the
                comm. Defaults to False.

        """
        self._close_backlog(wait=True)
        self._close_direct()
        super(AsyncComm, self)._close(linger=linger)

    @property
    def is_open(self):
        r"""bool: True if the backlog is open."""
        return self.is_open_direct or self.is_open_backlog

    @property
    def is_open_direct(self):
        r"""bool: True if the direct comm is not None."""
        return False

    @property
    def is_open_backlog(self):
        r"""bool: True if the backlog thread is running."""
        return self.backlog_open

    @property
    def n_msg_direct(self):
        r"""int: Number of messages currently being routed."""
        return 0

    @property
    def n_msg_recv(self):
        r"""int: Number of messages in the receive backlog."""
        if self.is_open_backlog:
            return len(self.backlog_recv)
        return 0

    @property
    def n_msg_send(self):
        r"""int: Number of messages in the send backlog."""
        if self.is_open_backlog:
            return len(self.backlog_send)
        return 0

    @property
    def n_msg_recv_drain(self):
        r"""int: Number of messages in the receive backlog and direct comm."""
        return self.n_msg_direct + self.n_msg_recv

    @property
    def n_msg_send_drain(self):
        r"""int: Number of messages in the send backlog and direct comm."""
        return self.n_msg_direct + self.n_msg_send

    @property
    def backlog_recv(self):
        r"""list: Messages that have been received."""
        with self.backlog_thread.lock:
            return self._backlog_recv

    @property
    def backlog_send(self):
        r"""list: Messages that should be sent."""
        with self.backlog_thread.lock:
            return self._backlog_send

    def add_backlog_recv(self, msg):
        r"""Add a message to the backlog of received messages.

        Args:
            msg (str): Received message that should be backlogged.

        """
        with self.backlog_thread.lock:
            self.debug("Added %d bytes to recv backlog.", len(msg))
            self._backlog_recv.append(msg)
            self.backlog_recv_ready.set()

    def add_backlog_send(self, msg):
        r"""Add a message to the backlog of messages to be sent.

        Args:
            msg (str): Message that should be backlogged for sending.

        """
        with self.backlog_thread.lock:
            self.debug("Added %d bytes to send backlog.", len(msg))
            self._backlog_send.append(msg)
            self.backlog_send_ready.set()

    def pop_backlog_recv(self):
        r"""Pop a message from the front of the recv backlog.

        Returns:
            str: First backlogged recv message.

        """
        with self.backlog_thread.lock:
            msg = self._backlog_recv.pop(0)
            self.debug("Popped %d bytes from recv backlog.", len(msg))
            if len(self._backlog_recv) == 0:
                self.backlog_recv_ready.clear()
        return msg

    def pop_backlog_send(self):
        r"""Pop a message from the front of the send backlog.

        Returns:
            str: First backlogged send message.

        """
        with self.backlog_thread.lock:
            msg = self._backlog_send.pop(0)
            self.debug("Popped %d bytes from send backlog.", len(msg))
            if len(self._backlog_send) == 0:
                self.backlog_send_ready.clear()
        return msg

    def run_backlog_send(self):
        r"""Continue trying to send buffered messages."""
        # flag = self.backlog_send_ready.wait(self.sleeptime)
        if not self.is_open_backlog:
            self._close_backlog()
            return
        # if flag:
        if not self.send_backlog():
            self._close_backlog()
            return
        self.sleep()

    def run_backlog_recv(self):
        r"""Continue buffering received messages."""
        if self.backlog_thread.main_terminated:
            self.close()
        if not self.is_open_backlog:
            self._close_backlog()
            return
        if not self.recv_backlog():
            # Stop the thread, but don't close the backlog
            self.backlog_thread.set_break_flag()
            return
        self.sleep()

    def send_backlog(self):
        r"""Send a message from the send backlog to the queue."""
        if len(self.backlog_send) == 0:
            return True
        try:
            flag = self._send_direct(self.backlog_send[0])
            if flag:
                self.pop_backlog_send()
        except AsyncTryAgain:  # pragma: debug
            flag = True
        except BaseException:  # pragma: debug
            self.exception('Error sending backlogged message')
            flag = False
        return flag

    def recv_backlog(self):
        r"""Check for any messages in the queue and add them to the recv
        backlog."""
        try:
            flag, data = self._recv_direct(timeout=0)
            if flag and data:
                self.add_backlog_recv(data)
                self.debug('Backlogged received message.')
        except BaseException:  # pragma: debug
            self.exception('Error receiving into backlog.')
            flag = False
        return flag

    def _send_direct(self, payload):
        r"""Send a message to the comm directly.

        Args:
            payload (str): Message to send.

        Returns:
            bool: Success or failure of sending the message.

        """
        return False

    def _recv_direct(self, timeout=None):
        r"""Receive a message from the comm directly.

        Args:
            timeout (float, optional): Time in seconds to wait for a message.
                Defaults to self.recv_timeout.

        Returns:
            tuple (bool, str): The success or failure of receiving a message
                and the message received.

        """
        return (False, self.empty_msg)

    def _send(self, payload, no_backlog=False):
        r"""Send a message to the backlog.

        Args:
            payload (str): Message to send.
            no_backlog (bool, optional): If False, any messages that can't be
                sent because the queue is full will be added to a list of
                messages to be sent once the queue is no longer full. If True,
                messages are not backlogged and an error will be raised if the
                queue is full.

        Returns:
            bool: Success or failure of sending the message.

        """
        if not self.is_open_direct:  # pragma: debug
            return False
        if no_backlog or not self.backlog_send_ready.is_set():
            if self._send_direct(payload):
                return True
        self.add_backlog_send(payload)
        self.debug('%d bytes backlogged', len(payload))
        return True

    def _recv(self, timeout=None, no_backlog=False):
        r"""Receive a message from the backlog.

        Args:
            timeout (float, optional): Time in seconds to wait for a message.
                Defaults to self.recv_timeout.
            no_backlog (bool, optional): If False and there are messages in the
                receive backlog, they will be returned first. Otherwise the
                queue is checked for a message.

        Returns:
            tuple (bool, str): The success or failure of receiving a message
                and the message received.

        """
        if timeout is None:
            timeout = self.recv_timeout
        # If no backlog, receive from queue
        if no_backlog:
            T = self.start_timeout(timeout)
            while ((not T.is_out) and (self.n_msg_direct == 0) and
                   self.is_open_direct):
                self.sleep()
            self.stop_timeout()
            return self._recv_direct()
        # Sleep until there is a message
        T = self.start_timeout(timeout)
        while (not T.is_out) and (not self.backlog_recv_ready.is_set()):
            self.backlog_recv_ready.wait(self.sleeptime)
        self.stop_timeout()
        # Return False if the queue is closed
        if self.is_closed or self.backlog_thread.was_break:  # pragma: debug
            self.debug("Backlog closed")
            return (False, self.empty_msg)
        # Return True, '' if there are no messages
        if not self.backlog_recv_ready.is_set():
            self.verbose_debug("No messages waiting.")
            return (True, self.empty_msg)
        # Return backlogged message
        self.debug('Returning backlogged received message')
        return (True, self.pop_backlog_recv())

    def purge(self):
        r"""Purge all messages from the comm."""
        super(AsyncComm, self).purge()
        with self.backlog_thread.lock:
            self.backlog_recv_ready.clear()
            self.backlog_send_ready.clear()
            self._backlog_recv = []
            self._backlog_send = []