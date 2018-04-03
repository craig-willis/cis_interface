import os
from cis_interface import timing
from cis_interface.drivers.MatlabModelDriver import _matlab_installed


def test_get_source():
    r"""Test getting source file for test."""
    lang_list = ['python', 'c', 'cpp', 'matlab']
    dir_list = ['src', 'dst']
    for l in lang_list:
        for d in dir_list:
            fname = timing.get_source(l, d)
            assert(os.path.isfile(fname))


def test_combos():
    r"""Test different combinations of source/destination languages."""
    lang_list = ['python', 'c', 'cpp']
    if _matlab_installed:
        lang_list.append('matlab')
    for l1 in lang_list:
        for l2 in lang_list:
            x = timing.TimedRun(l1, l2)
            x.run(1, 10)


def test_scaling_count():
    r"""Test running scaling with number of messages."""
    x = timing.TimedRun('python', 'python')
    x.scaling_count(10, nsamples=1)


def test_scaling_size():
    r"""Test running scaling with size of messages."""
    x = timing.TimedRun('python', 'python')
    x.scaling_size(1, nsamples=1)


def test_plot_scaling():
    x = timing.TimedRun('python', 'python')
    x1, y1 = x.scaling_count(10, nsamples=1)
    x.plot_scaling(x1, y1, 'count')
    x2, y2 = x.scaling_size(1, nsamples=1)
    x.plot_scaling(x2, y2, 'size', scaling='log')