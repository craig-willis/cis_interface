import numpy as np
import nose.tools as nt
from cis_interface.drivers.IODriver import maxMsgSize
from cis_interface.backwards import pickle
from cis_interface.drivers.tests import test_Driver as parent
from cis_interface.tools import ipc_queues


class IOInfo(object):
    r"""Simple class for useful IO attributes.

    Attributes:
        fmt_str (str): Format string for lines of a table.
        file_rows (list): List of mock table rows.

    """

    def __init__(self):
        self.fmt_str = '%5s\t%d\t%f\n'
        self.fmt_str_line = '# ' + self.fmt_str
        self.file_dtype = 'S5, i4, f8'
        self.file_rows = [('one', int(1), 1.0),
                          ('two', int(2), 2.0),
                          ('three', int(3), 3.0)]
        
    @property
    def file_lines(self):
        r"""list: Lines in a mock file."""
        out = []
        for r in self.file_rows:
            out.append(self.fmt_str % r)
        return out

    @property
    def file_contents(self):
        r"""str: Complete contents of mock file."""
        out = self.fmt_str_line
        for line in self.file_lines:
            out += line
        return out

    @property
    def file_array(self):
        r"""np.ndarray: Numpy structure array of mock file contents."""
        out = np.zeros(len(self.file_rows), dtype=self.file_dtype)
        for i, row in enumerate(self.file_rows):
            out[i] = row
        return out

    @property
    def file_bytes(self):
        r"""str: Raw bytes of array of mock file contents."""
        arr = self.file_array
        out = ''
        for n in arr.dtype.names:
            out += arr[n].tobytes()
        return out

    @property
    def data_dict(self):
        r"""dict: Mock dictionary of arrays."""
        if not hasattr(self, '_data_dict'):
            self._data_dict = {
                # 1D arrays are converted to 2D (as row) when saved
                # 'w': np.zeros((5,), dtype=np.int32),
                'x': np.zeros((5,1), dtype=np.int32),
                'y': np.zeros((1,5), dtype=np.int64),
                'z': np.ones((3,4), dtype=np.float64)}
        return self._data_dict

    @property
    def pickled_data(self):
        r"""str: Pickled mock data dictionary."""
        return pickle.dumps(self.data_dict)

    @property
    def maxMsgSize(self):
        r"""int: Maximum message size."""
        return maxMsgSize

    @property
    def msg_short(self):
        r"""str: Small test message for sending."""
        return 'Test message'

    @property
    def msg_long(self):
        r"""str: Small test message for sending."""
        return 'Test message' + self.maxMsgSize*'0'


class TestIODriver(parent.TestDriver, IOInfo):
    r"""Test class for the IODriver class.

    Attributes (in addition to parent class's):
        fmt_str (str): Format string for lines of a table.
        file_rows (list): List of mock table rows.

    """

    def __init__(self):
        super(TestIODriver, self).__init__()
        IOInfo.__init__(self)
        self.driver = 'IODriver'
        self.args = '_TEST'
        self.attr_list += ['state', 'numSent', 'numReceived', 'env', 'mq']
        self.nprev_queues = 0

    def setup(self):
        r"""Get a count of existing queues."""
        self.nprev_queues = len(ipc_queues())
        super(TestIODriver, self).setup()

    def teardown(self):
        r"""Make sure that all new message queues were deleted."""
        super(TestIODriver, self).teardown()
        nt.assert_equal(len(ipc_queues()), self.nprev_queues)

    def test_early_close(self):
        r"""Test early deletion of message queue."""
        if self.instance.mq:
            self.instance.mq.remove()
            self.instance.mq = None

    def test_send_recv(self):
        r"""Test sending/receiving small message."""
        self.instance.ipc_send(self.msg_short)
        msg_recv = self.instance.ipc_recv()
        nt.assert_equal(msg_recv, self.msg_short)

    def test_send_recv_nolimit(self):
        r"""Test sending/receiving large message."""
        assert(len(self.msg_long) > self.maxMsgSize)
        self.instance.ipc_send_nolimit(self.msg_long)
        msg_recv = self.instance.ipc_recv_nolimit()
        nt.assert_equal(msg_recv, self.msg_long)

    def assert_before_stop(self):
        r"""Assertions to make before stopping the driver instance."""
        super(TestIODriver, self).assert_before_stop()
        assert(self.instance.mq)

    def run_before_terminate(self):
        r"""Commands to run while the instance is running, before terminate."""
        self.instance.ipc_send(self.msg_short)

    def assert_after_terminate(self):
        r"""Assertions to make after terminating the driver instance."""
        super(TestIODriver, self).assert_after_terminate()
        assert(not self.instance.mq)


