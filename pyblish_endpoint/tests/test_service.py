from nose.tools import *

import pyblish_endpoint.service


def test_service_standalone():
    """Service is callable on its own"""
    service = pyblish_endpoint.service.MockService()

    insts = service.instances()
    eq_(len(insts) > 0, True)
