from nose.tools import *


from pyblish_endpoint import service
from pyblish_endpoint import mocking


def test_service_standalone():
    """Service is callable on its own"""
    s = mocking.MockService()
    s.init()

    insts = list(s.context)
    eq_(len(insts) > 0, True)
