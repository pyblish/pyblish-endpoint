from nose.tools import *

import pyblish_endpoint.mocking


def test_service_standalone():
    """Service is callable on its own"""
    service = pyblish_endpoint.mocking.MockService()
    service.init()

    insts = list(service.context)
    eq_(len(insts) > 0, True)
