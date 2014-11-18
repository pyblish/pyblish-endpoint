
import json

from nose.tools import *
from pyblish_endpoint import tests

app = tests.app


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
    func = getattr(app, verb.lower())
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

    data = json.loads(response.data)

    eq_(isinstance(data, basestring), True)


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

    process_id = json.loads(response.data)

    response = request("GET", "/processes/%s" % process_id)
    check_status(response, 200)

    # Expected keys at included in returned data (at least)
    data = json.loads(response.data)
    check_keys(data, ["process_id", "running", "messages"])


def test_application_stats():
    """GET /application returns application statistics"""
    response = request("GET", "/application")
    check_content_type(response)
    check_status(response, 200)

    data = json.loads(response.data)
    check_keys(data, ["host", "port",
                      "pyblishVersion", "endpointVersion",
                      "pythonVersion", "user", "connectTime"])
