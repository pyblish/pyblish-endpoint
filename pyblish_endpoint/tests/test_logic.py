import json
import logging
from nose.tools import *

from pyblish_endpoint import server, service

import lib

app, api = server.create_app()
app.config["TESTING"] = True
client = app.test_client()
client.testing = True

log = logging.getLogger("endpoint")
log.setLevel(logging.WARNING)

service.register_service(lib.TestService, force=True)


def setup():
    init()


# Helper functions

def check_content_type(response):
    """Ensure content type is JSON"""
    eq_(response.headers['Content-Type'], 'application/json')


def check_status(response, status):
    """Ensure response.status_code == `status`"""
    eq_(response.status_code, status)


def check_keys(data, keys):
    """Ensure `keys` are available in `data`"""
    eq_(set(keys).issubset(data.keys()), True)


def load_data(response):
    return json.loads(response.data)


def request(verb, address, *args, **kwargs):
    func = getattr(client, verb.lower())
    return func("/pyblish/v1" + address, *args, **kwargs)


def init():
    response = request("POST", "/session")
    check_content_type(response)
    check_status(response, 200)
