"""Pyblish Endpoint Server

| Endpoint                | Description
|-------------------------|--------------
| /processes              | List processes
| /processes/<id>         | Query process
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


for _endpoint, _resource in resource_map.items():
    api.add_resource(_resource, prefix + _endpoint)


@app.route("/shutdown", methods=["POST"])
def shutdown():
    """Shutdown server

    Utility endpoint for remotely shutting down server.

    :status 200: Server successfully shutdown
    :status 400: Could not shut down

    :>json bool ok: Operation status, not returned on error
    :>json string message: Error message

    **Example Request**

    .. sourcecode:: http

        GET /shutdown
        Host: localhost
        Accept: application/json

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: application/json

        {"ok": true}

    """

    log.info("Server shutting down...")

    func = flask.request.environ.get("werkzeug.server.shutdown")
    if func is not None:
        func()
    else:
        return {"message": "Could not shutdown server"}, 400

    log.info("Server stopped")

    return {"ok": True}, 200


if __name__ == '__main__':
    app.run(port=6000, debug=True)
