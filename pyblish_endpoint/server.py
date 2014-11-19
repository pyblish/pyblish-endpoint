"""Pyblish Endpoint Server

| Endpoint                | Description
|-------------------------|--------------
| /processes              | List processes
| /processes/<id>         | Query and manipulate process
| /instances              | List instances
| /instances/<id>         | Query instance
| /instances/<id>/nodes   | List nodes
| /instances/<id>/data    | Query and manipulate data

"""

# Standard library
import os
import sys
import logging

log = logging.getLogger("endpoint")

# Register vendor packages
package_dir = os.path.dirname(__file__)
vendor_dir = os.path.join(package_dir, "vendor")
sys.path.insert(0, vendor_dir)

# Dependencies
import flask
import flask.ext.restful

# Local library
import service
import resource

app = flask.Flask(__name__)
api = flask.ext.restful.Api(app)
resource.setup_message_queue()

prefix = "/pyblish/v0.1"
resource_map = {
    "/processes": resource.ProcessesListApi,
    "/processes/<process_id>": resource.ProcessesApi,
    "/application": resource.ApplicationApi,
    "/instances": resource.InstancesListApi,
    "/instances/<instance_id>": resource.InstancesApi,
    "/instances/<instance_id>/nodes": resource.NodesListApi,
    "/instances/<instance_id>/data": resource.DataListApi,
    "/instances/<instance_id>/data/<data_id>": resource.DataApi,
}

endpoint_map = {
    "/processes/<process_id>":          "process",
    "/processes":                       "processes",
    "/application":                     "application",
    "/instances/<instance_id>":         "instance",
    "/instances":                       "instances",
    "/instances/<instance_id>/nodes":   "instanceNodes",
    "/instances/<instance_id>/data":    "instanceData"
}

# Map resources to URIs
for uri, _resource in resource_map.items():
    endpoint = endpoint_map.get(uri)
    api.add_resource(_resource, prefix + uri, endpoint=endpoint)

# Map utility URIs
app.route("/shutdown", methods=["POST"])(resource.shutdown)


def start_debug_server(port, **kwargs):
    formatter = logging.Formatter("%(levelname)-8s %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    os.environ["ENDPOINT_PORT"] = str(port)

    service.MockService.SLEEP = 3
    service.register_service(service.MockService)
    app.run(debug=True, port=port)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=6000, help="Port to use")

    args = parser.parse_args()

    start_debug_server(**args.__dict__)
