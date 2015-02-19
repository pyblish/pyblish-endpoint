"""Endpoint resources

Attributes:
    log: Current logger

"""

# Standard library
import sys
import json
import uuid
import logging
import traceback

# Dependencies
import pyblish.api
import flask.ext.restful
import flask.ext.restful.reqparse

# Local library
from service import current_service

log = logging.getLogger("endpoint")


def unique_id():
    """Return a universally unique identifier

    Using as few characters as possible. The condition is
    that a process is typically executed 1 at a time, at
    a given rate of 2/second, and shall remain referencable
    for a short period of time (10-20 minutes) after first
    being created.

    """

    return uuid.uuid4().hex[:5]


def format_error(error):
    fname, line_no, func, exc = error.traceback
    return {
        "message": str(error),
        "fname": fname,
        "line_number": line_no,
        "func": func,
        "exc": exc
    }


def format_instance(instance):
    return {
        "name": instance.data("name"),
        "family": instance.data("family"),
        "objName": instance.name,
        "category": getattr(instance, "category", None),
        "nodes": [str(x) for x in instance],
        "data": dict((str(k), str(v)) for k, v in instance._data.iteritems()),
        "publish": instance.data("publish"),
        "doc": instance.data("doc")
    }


def format_plugin(plugin):
    formatted = {
        "name": plugin.__name__,
        "version": plugin.version,
        "requires": plugin.requires,
        "order": plugin.order,
        "active": False,
        "optional": plugin.optional,
        "doc": getattr(plugin, "doc", plugin.__doc__)
    }

    try:
        # The MRO is as follows: (-1)object, (-2)Plugin, (-3)Selector..
        formatted["type"] = plugin.__mro__[-3].__name__
    except IndexError:
        # Plug-in was not subclasses from any of the
        # provided superclasses of pyblish.api. This
        # is either a bug or some (very) custom behavior
        # on the users part.
        log.critical("This is a bug")
        formatted["type"] = "Invalid"

    for attr in ("hosts", "families"):
        if hasattr(plugin, attr):
            formatted[attr] = getattr(plugin, attr)

    return formatted


class ApplicationApi(flask.ext.restful.Resource):
    """Application API

    GET /application

    """

    def get(self):
        """Return application statistics

        :>json string host
        :>json string port
        :>json string pyblishVersion
        :>json string endpointVersion
        :>json string pythonVersion
        :>json string user
        :>json string connectTime

        :status 200: Application statistics returned

        """

        data = {}

        data.update(current_service().system())
        data.update(current_service().versions())

        return data, 200


class ApplicationShutdownApi(flask.ext.restful.Resource):
    def post(self):
        """Shutdown server

        Utility resource for remotely shutting down server.

        :status 200: Server successfully shutdown
        :status 400: Could not shut down

        :>json bool ok: Operation status, not returned on error
        :>json string message: Error message

        **Example Request**

        .. sourcecode:: http

            POST /shutdown
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


class SessionApi(flask.ext.restful.Resource):
    """Create and populate Context in host

    POST /session

    """

    def post(self):
        try:
            status = current_service().init()
        except Exception:
            _, _, exc_tb = sys.exc_info()
            tb = traceback.extract_tb(exc_tb)[-1]
            return {"message": tb}, 500

        return {"ok": status}, 200

    def delete(self):
        pass


class StateApi(flask.ext.restful.Resource):
    """Pass GUI state to host for processing

    GET /state
    POST /state

    """

    def get(self):
        return {"ok": True, "state": current_service().state}

    def post(self):
        parser = flask.ext.restful.reqparse.RequestParser()

        parser.add_argument("state",
                            type=str,
                            required=True,
                            help="Must pass state")

        kwargs = parser.parse_args()

        try:
            state = json.loads(kwargs["state"])
        except:
            message = "Could not de-serialise state: %r" % kwargs
            log.error(message)
            return {"ok": False, "message": message}, 500

        current_service().state = state
        return {"ok": True, "state": state}, 200


class NextApi(flask.ext.restful.Resource):
    """Process next item in state

    POST /next

    """

    def post(self):
        result = current_service().next()

        if result is not None:
            plugin = result["plugin"]
            instance = result["instance"]
            error = result["error"]
            records = result["records"]

            output = {
                "plugin": plugin.__name__,
                "error": None,
                "records": [r.__dict__ for r in records]
            }

            if instance is not None:
                output["instance"] = instance.data("name")

            if error is not None:
                output["error"] = error.__dict__
                output["error"]["message"] = error.message

            return output, 200

        return {"ok": True}, 404


class ContextApi(flask.ext.restful.Resource):
    def get(self):
        """Get data about context"""


class PluginsListApi(flask.ext.restful.Resource):
    def get(self):
        """Get available plug-ins

        :>jsonarr string name: Name of plugin
        :>jsonarr array families: Supported families
        :>jsonarr array hosts: Supported hosts
        :>jsonarr string version: Plug-in version
        :>jsonarr string requires: Plug-in requirement

        :status 200: Plug-ins returned

        """

        plugins = current_service().plugins
        context = current_service().context

        families = set()
        for instance in context:
            families.add(instance.data("family"))

        response = []
        for plugin in plugins:
            formatted = format_plugin(plugin)

            if hasattr(plugin, "families"):
                if pyblish.api.instances_by_plugin(context, plugin):
                    formatted["active"] = True

            response.append(formatted)

        return response, 200


class InstancesListApi(flask.ext.restful.Resource):
    """

    GET /instances

    """

    def get(self):
        """Get all available instances

        :>jsonarr string name: Name of instance
        :>jsonarr string objName: Name of instance
        :>jsonarr string family: All contained nodes of instance
        :>jsonarr bool publish: Should instance be published?
        :>jsonarr array nodes: Array of included nodes
        :>jsonarr obj data: Instance metadata

        :status 200: Instances returned successfully

        **Example response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            [
                {
                    "name": "Instance01",
                    "objName": "Instance01_:publish_SEL",
                    "family": "napoleon.asset.rig"
                },
                {
                    "name": "Instance02",
                    "objName": "Instance02_:pointcache_SEL",
                    "family": "napoleon.animation.pointcache"
                },
            ]

        """

        instances = list(current_service().context)

        response = []
        for instance in instances:
            response.append(format_instance(instance))

        return response, 200


def find_instance(name, col):
    return filter(lambda i: i.data("name") == name, col)[0]


class InstancesApi(flask.ext.restful.Resource):
    def get(self, instance_id):
        """Query links to instance resources

        :>json string nodes: Link to nodes of instance
        :>json string data: Link to data of instance

        :status 200: Links returned

        """

        instances = list(current_service().context)

        try:
            instance = find_instance(instance_id, instances)
        except IndexError:
            return {"message": "%s not found" % instance_id}, 404

        response = format_instance(instance)
        response["_links"] = [
            {"rel": "/nodes"},
            {"rel": "/data"}
        ]

        return response, 200


class NodesListApi(flask.ext.restful.Resource):
    def get(self, instance_id):
        """Get nodes of instance `instance_id`

        :>jsonarr name: Name of node

        :status 200: Nodes returned successfully
        :status 404: instance_id was not found

        """

        instances = list(current_service().context)

        try:
            instance = find_instance(instance_id, instances)
        except IndexError:
            return {"message": "instance_id %s not found" % instance_id}, 404

        return list(instance), 200


class DataListApi(flask.ext.restful.Resource):
    """API for instance data

    Each instance contains some amount of additional data, known
    as metadata. This includes both internal data, such as it's
    family, along with external - user customisable - data, such
    as at which frame an animation is to start.

    """

    def get(self, instance_id):
        """Get data of instance

        :status 200: Data was returned successfully
        :status 404: instance_id was not found

        :>json obj data: Available data returned as object

        """

        instances = list(current_service().context)

        try:
            instance = find_instance(instance_id, instances)
        except IndexError:
            return {"message": "instance_id %s not found" % instance_id}, 404

        try:
            json.dumps(instance.data())
        except:
            return {"message": "Instance data could not "
                    "be JSON serialised"}, 500

        return instance.data(), 200


class DataApi(flask.ext.restful.Resource):
    """API for individual items of data

    GET /instances/<id>/data/<id>
    PUT /instances/<id>/data/</id>
    DELETE /instances/<id>/data/<id>

    """

    def get(self, instance_id, data_id):
        pass
