from nose.tools import *

from .. import service


def test_service_standalone():
    """Service is callable on its own"""
    s = service.EndpointService()
    s.init()
