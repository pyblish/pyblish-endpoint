import json
import logging
from nose.tools import *

from pyblish_endpoint import server
from pyblish_endpoint import service

import lib

app, api = server.create_app()
app.config["TESTING"] = True
client = app.test_client()
client.testing = True

log = logging.getLogger()
log.setLevel(logging.WARNING)


def setup():
    service.register_service(lib.TestService, force=True)
    response = request("POST", "/session")
    check_content_type(response)
    check_status(response, 200)


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


# Tests
@with_setup(setup)
def test_instances():
    """GET /instances returns available instances"""

    response = request("GET", "/instances")

    # Check for application/json
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)

    eq_(len(data), len(lib.INSTANCES))

    instance = data[0]
    check_keys(instance, ["name", "family",
                          "children", "data", "publish"])


@with_setup(setup)
def test_no_instances():
    """When there are no instances, it should still return an array"""
    response = request("GET", "/instances")
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)
    eq_(isinstance(data, list), True)


@with_setup(setup)
def test_instance():
    """GET /instances/<instance> returns links to child resources"""
    response = request("GET", "/instances/Peter01")
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)

    assert data, "%r is empty!" % data

    check_keys(data, ["children", "data"])


@with_setup(setup)
def test_instance_nodes():
    """GET /instances/<id>/nodes returns all nodes within instance_id"""
    response = request("GET", "/instances/Peter01/nodes")
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)
    eq_(len(data), 3)  # Peter01 always has 3 child nodes

    # Node only has a single key
    node = data[0]
    eq_(isinstance(node, basestring), True)


@with_setup(setup)
def test_instance_nodes_instance_not_exists():
    """Instance "Peter02" doesn't exist"""
    response = request("GET", "/instances/Peter02/nodes")
    check_content_type(response)
    check_status(response, 404)


@with_setup(setup)
def test_instance_not_exists():
    """Instance "Peter02" doesn't exist"""
    response = request("GET", "/instances/Peter02/nodes")
    check_content_type(response)
    check_status(response, 404)


@with_setup(setup)
def test_instance_data():
    """GET /instances/<id>/data returns data within instance"""
    response = request("GET", "/instances/Peter01/data")
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)
    check_keys(data, ["identifier", "minWidth",
                      "assetSource", "destination"])


@with_setup(setup)
def test_plugins():
    """GET /plugins returns available plugins"""
    response = request("GET", "/plugins")
    check_content_type(response)
    check_status(response, 200)

    plugins = load_data(response)
    eq_(isinstance(plugins, list), True)
    eq_(len(plugins) >= len(lib.PLUGINS), True)

    plugin = plugins[0]
    check_keys(plugin, ["name", "version", "requires"])
    eq_(isinstance(plugin["families"], list), True)


@with_setup(setup)
def test_application_stats():
    """GET /application returns application statistics"""
    response = request("GET", "/application")
    check_content_type(response)
    check_status(response, 200)

    data = load_data(response)
    check_keys(data, ["host", "port",
                      "pyblishVersion", "endpointVersion",
                      "pythonVersion", "user", "connectTime"])


@with_setup(setup)
def test_server_shutdown():
    """Can't shutdown from test, but the call works as expected"""
    response = request("POST", "/application/shutdown")
    check_content_type(response)
    check_status(response, 400)


@with_setup(setup)
def test_post_state():
    """State must be passed before calling next"""
    original_state = {"instances": ["Richard11", "Peter01"],
                      "plugins": ["ValidateNamespace"]}

    serialised_state = json.dumps(original_state)
    response = request("POST", "/state",
                       data={"state": serialised_state})
    check_content_type(response)
    check_status(response, 200)
    data = load_data(response)
    assert "ok" in data
    assert "state" in data

    assert isinstance(data["state"], dict)
    assert data["state"].keys() == original_state.keys(), repr(data)

    # GET returns the identical state

    response = request("GET", "/state")
    check_content_type(response)
    check_status(response, 200)
    data = load_data(response)
    assert "ok" in data, data
    assert "state" in data, data
    assert data["state"].keys() == original_state.keys(), repr(data)


@with_setup(setup)
def test_post_next():
    """POST to /next causes processing of next item in state"""

    # Set state
    original_state = {"context": ["Steven11", "Richard05"],
                      "plugins": ["ValidateNamespace"]}

    serialised_state = json.dumps(original_state)
    request("POST", "/state", data={"state": serialised_state})

    response = request("GET", "/state")
    check_content_type(response)
    check_status(response, 200)
    data = load_data(response)
    assert_equal(original_state, data["state"])
    assert_equal(data["state"]["context"][0], "Steven11")

    # Next
    response = request("POST", "/next")
    check_content_type(response)
    check_status(response, 200)

    # Processing should now be done, and `data`
    # should contain the results
    data = load_data(response)
    assert "records" in data, data
    assert data["plugin"] == "ValidateNamespace"
    assert data["instance"] == "Steven11", data

    # Next, again
    response = request("POST", "/next")
    check_content_type(response)
    check_status(response, 200)

    # This time we should be processing the next instance
    data = load_data(response)
    assert "records" in data, data
    assert data["plugin"] == "ValidateNamespace"
    assert data["instance"] == "Richard05", data

    # There is now no more instances to process
    response = request("POST", "/next")
    check_content_type(response)
    check_status(response, 404)
