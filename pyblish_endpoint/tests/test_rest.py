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


def mock_instances_teardown():
    service.MockService.NUM_INSTANCES = 2


def mock_instances_setup():
    service.MockService.NUM_INSTANCES = 0


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
    return func("/pyblish/v0.1" + address, *args, **kwargs)


# Tests

def test_instances():
    """GET /instances returns available instances"""
    response = request("GET", "/instances")

    # Check for application/json
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)

    # 2 instances are hardcoded by default
    eq_(len(data), 2)

    instance = data[0]
    check_keys(instance, ["name", "family", "objName"])


@with_setup(mock_instances_setup, mock_instances_teardown)
def test_no_instances():
    """When there are no instances, it should still return an array"""
    response = request("GET", "/instances")
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)
    eq_(isinstance(data, list), True)


def test_instance():
    """GET /instances/<instance> returns links to child resources"""
    response = request("GET", "/instances/Peter01")
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)

    assert data, "%r is empty!" % data

    check_keys(data, ["nodes", "data"])


def test_instance_nodes():
    """GET /instances/<id>/nodes returns all nodes within instance"""
    response = request("GET", "/instances/Peter01/nodes")
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)
    eq_(len(data), 3)  # 3 nodes have been hardcoded

    # Node only has a single key
    node = data[0]
    check_keys(node, ["name"])


def test_instance_nodes_instance_not_exists():
    """Instance "Peter02" doesn't exist"""
    response = request("GET", "/instances/Peter02/nodes")
    check_content_type(response)
    check_status(response, 404)


def test_instance_not_exists():
    """Instance "Peter02" doesn't exist"""
    response = request("GET", "/instances/Peter02/nodes")
    check_content_type(response)
    check_status(response, 404)


def test_instance_data():
    """GET /instances/<id>/data returns data within instance"""
    response = request("GET", "/instances/Peter01/data")
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)
    eq_(len(data), 4)  # 4 keys have been hardcoded
    check_keys(data, ["identifier", "minWidth",
                      "assetSource", "destination"])


def test_post_process():
    """POST to /processes returns a unique ID"""
    response = request("POST", "/processes",
                       data={"instance": "Peter01",
                             "plugin": "ValidateNamespace"})

    check_content_type(response)
    check_status(response, 201)

    data = load_data(response)

    check_keys(data, ["process_id", "_next"])


def test_get_process():
    """GET /processes/<process_id> returns information about the process"""

    # Getting a non-existant ID returns status code 400
    process_id = "notexist"
    response = request("GET", "/processes/%s" % process_id)
    check_content_type(response)
    check_status(response, 404)

    # Creating a new process works fine
    response = request("POST", "/processes",
                       data={"instance": "Peter01",
                             "plugin": "ValidateNamespace"})
    check_content_type(response)
    check_status(response, 201)

    data = load_data(response)
    process_id = data["process_id"]

    response = request("GET", "/processes/%s" % process_id)
    check_status(response, 200)

    # Expected keys at included in returned data (at least)
    data = json.loads(response.data)
    check_keys(data, ["process_id", "running"])


def test_application_stats():
    """GET /application returns application statistics"""
    response = request("GET", "/application")
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)
    check_keys(data, ["host", "port",
                      "pyblishVersion", "endpointVersion",
                      "pythonVersion", "user", "connectTime"])


def test_process_logging():
    """Each process maintains its own log"""
    response = request("POST", "/processes",
                       data={"instance": "Peter01",
                             "plugin": "ValidateNamespace"})
    check_content_type(response)
    check_status(response, 201)
    data = load_data(response)

    # There should be messages in the queue by now
    response = request("GET", "/processes/%s" % data["process_id"])
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)
    check_keys(data, ["process_id", "running"])


@timed(1.5)
def test_post_performance():
    """Posting should be fast"""
    for x in xrange(100):
        response = request("POST", "/processes",
                           data={"instance": "Peter%02d" % x,
                                 "plugin": "ValidateNamespace"})
        check_content_type(response)
        check_status(response, 201)


def test_server_shutdown():
    """Can't shutdown from test, but the call works as expected"""
    response = request("POST", "/application/shutdown")
    check_content_type(response)
    check_status(response, 400)


def test_list_processes():
    """Listing processes works fine"""

    # Make a process
    response = request("POST", "/processes",
                       data={"instance": "Peter01",
                             "plugin": "ValidateNamespace"})
    check_content_type(response)
    check_status(response, 201)
    data = load_data(response)
    process_id = data["process_id"]

    # This process should now be gettable
    response = request("GET", "/processes")
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)
    matches = filter(lambda p: p["process_id"] == process_id, data)
    eq_(len(matches), 1)


def test_modify_process():
    """PUT /processes/<process_id> is not yet implemented"""

    # Make a process
    response = request("POST", "/processes",
                       data={"instance": "Peter01",
                             "plugin": "ValidateNamespace"})
    check_content_type(response)
    check_status(response, 201)
    data = load_data(response)
    process_id = data["process_id"]

    response = request("PUT", "/processes/%s" % process_id,
                       data={"running": False})
    check_content_type(response)
    check_status(response, 501)


def test_delete_process():
    """DELETE /processes/<process_id> is not yet implemented"""

    # Make a process
    response = request("POST", "/processes",
                       data={"instance": "Peter01",
                             "plugin": "ValidateNamespace"})
    check_content_type(response)
    check_status(response, 201)
    data = load_data(response)
    process_id = data["process_id"]

    response = request("DELETE", "/processes/%s" % process_id)
    check_content_type(response)
    check_status(response, 501)


def test_logs():
    """GET /processes/<process_id>/logs yields log messages"""

    # First make a process, then look at it's logging messages
    response = request("POST", "/processes",
                       data={"instance": "Peter01",
                             "plugin": "ValidateNamespace"})
    check_content_type(response)
    check_status(response, 201)
    data = load_data(response)
    process_id = data["process_id"]

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

    response = request("GET", "/processes/%s/logs" % process_id)
    check_content_type(response)
    check_status(response, 200)

    messages = load_data(response)
    eq_(isinstance(messages, list), True)
    eq_(len(messages) > 0, True)
    eq_(isinstance(messages[0], basestring), True)

    # Log should be empty now
    response = request("GET", "/processes/%s/logs" % process_id)
    check_content_type(response)
    check_status(response, 200)

    messages = load_data(response)
    assert len(messages) == 0, messages
