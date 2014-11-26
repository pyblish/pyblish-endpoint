import time
import json
import logging
from nose.tools import *

from pyblish_endpoint import server
from pyblish_endpoint import service

app, api = server.create_app()
app.config["TESTING"] = True
client = app.test_client()
client.testing = True

log = logging.getLogger("endpoint")

service.register_service(service.MockService, force=True)


def setup():
    init()


def wait_for_process(process_id):
    # Look at the log, but make sure the process has
    # completed running first.
    is_running = True
    count = 3
    while is_running and count >= 0:
        time.sleep(0.1)
        count -= 1

        response = request("GET", "/processes/%s" % process_id)
        check_content_type(response)
        check_status(response, 200)
        data = load_data(response)
        is_running = data["running"]

    if is_running:
        raise RuntimeError("Process took too long")


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


@with_setup(setup)
def test_validation_fail():
    """Failed validation returns indication of failure"""
    response = request("POST", "/processes",
                       data={"instance": "Richard05",
                             "plugin": "ValidateFailureMock"})

    check_content_type(response)
    check_status(response, 201)

    data = load_data(response)
    process_id = data["process_id"]

    # Block..
    wait_for_process(process_id)

    response = request("GET", "/processes/%s" % process_id)

    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)
    errors = data["errors"]
    eq_(len(errors), 1)
    error = data["errors"][0]
    eq_(error["message"], "Instance failed")
