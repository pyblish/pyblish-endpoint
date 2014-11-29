"""Endpoint resources

Attributes:
    process_logs: Logging messages, per process
    threads: Container of threads, stored under their unique ID
    log: Current logger

"""

# Standard library
import sys
import json
import uuid
import logging
import traceback
import threading

# Dependencies
import pyblish.api
import flask.ext.restful
import flask.ext.restful.reqparse

# Local library
from service import current_service

process_logs = {}
threads = {}

log = logging.getLogger("endpoint")


class MessageHandler(logging.Handler):
    """Intercept logging and store them in a list per process

    The list is emptied upon calling DELETE /processes/<process_id>

    """

    def __init__(self, thread, records, *args, **kwargs):
        super(MessageHandler, self).__init__(*args, **kwargs)
        self.thread = thread
        self.records = records

    def emit(self, record):
        # Do not record server messages
        if record.name in ["werkzeug"]:
            return

        # Only store records from current thread
        # WARNING: This won't work in Maya, because
        # Maya insists on running things in the main thread
        # which causes threadName to always be "MainThread"

        # if record.threadName == self.thread:
        #     self.records.append(record)

        # As a workaround, record everything.
        # NOTE: This is O(n) and thus much slower
        self.records.append(record)


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
        "nodes": list(instance),
        # "data": instance.data(),  # Temporarily disabled,
        "data": {},
        "publish": instance.data("publish")
    }


def format_plugin(plugin):
    formatted = {
        "name": plugin.__name__,
        "version": plugin.version,
        "requires": plugin.requires,
        "order": plugin.order,
        "active": False,
        "optional": plugin.optional
    }

    try:
        # The MRO is as follows: (-1)object, (-2)Plugin, (-3)Selector..
        formatted["type"] = plugin.__mro__[-3].__name__
    except IndexError:
        # Plug-in was not subclasses from any of the
        # provided superclasses of pyblish.api. This
        # is either a bug or some (very) custom behavior
        # on the users part.
        log.warning("In formatting this plug-in, it was discovered "
                    "that it hasn't been subclassed from an expected "
                    "superclass. Plugin and MRO: %s (%s)"
                    % (plugin, plugin.__mro__))
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


class ProcessesListApi(flask.ext.restful.Resource):
    """List processes API

    GET /processes
    POST /processes

    """

    def get(self):
        """Get all currently running processes

        :>jsonarr string process_id: Identifier of process

        :status 200: Processes returned successfully

        **Example response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            [
                {"process_id": 12345},
                {"process_id": 12346},
                {"process_id": 12347},
            ]

        """

        process_ids = []
        for process_id in threads.keys():
            process_ids.append({"process_id": process_id})

        return process_ids, 200

    def post(self):
        """Process instance with plug-in

        :param string instance: Instance to process
        :param string plugin: Plug-in used for processing

        :>json string process_id: Unique id of process
        :>json string _next: Link to where id may be used to
            query about process

        :status 201: Process was successfully created
        :status 400: Missing argument(s)

        """

        parser = flask.ext.restful.reqparse.RequestParser()

        parser.add_argument("instance",
                            type=str,
                            required=True,
                            help="Instance can't be blank")
        parser.add_argument("plugin",
                            type=str,
                            required=True,
                            help="Plugin can't be blank")

        kwargs = parser.parse_args()

        process_id = unique_id()
        kwargs["process_id"] = process_id

        def task(process_id, instance, plugin):
            try:
                result = current_service().process(instance, plugin)

                if isinstance(result, Exception):
                    threads[process_id]["errors"].append(result)

            except ValueError as e:
                log.error("Processing failure for %s|%s: %s"
                          % (instance, plugin, e))

        # Spawn task in new thread
        thread = threading.Thread(
            name=process_id,
            target=task,
            kwargs=kwargs)
        thread.deamon = True

        # Setup logger
        records = list()
        handler = MessageHandler(thread=thread.name, records=records)

        # Logger is deleted during GET /processes/<process_id>
        log = logging.getLogger()
        log.addHandler(handler)

        # Store references
        threads[process_id] = {"log": [records, handler],
                               "handle": thread,
                               "errors": []}

        thread.start()

        return {"process_id": process_id,
                "_next": "/processes/<process_id>"}, 201


class ProcessesApi(flask.ext.restful.Resource):
    """Query and manipulate processes API

    GET /processes/<process_id>
    PUT /processes/<process_id>
    DELETE /processes/<process_id>

    """

    def get(self, process_id=None):
        """Query a process

        :param process_id: Unique process identifier

        :>json string process_id: The identifier passed in
        :>json bool running: Current state of this process
        :>json array messages: List of queued messages

        :status 200: Process existed and was returned
        :status 404: process_id was not found

        The following is the signature of the **messages** array.

        :>jsonarr string name: Name of logger used to log the event
        :>jsonarr string msg: Actual logged message
        :>jsonarr string levelname: Level used for event
        :>jsonarr string filename: Filename in which event was logged
        :>jsonarr string pathname: Absolute path from which event was logged
        :>jsonarr string lineno: Line within filename event was logged
        :>jsonarr string funcName: Function used to log the event
        :>jsonarr string module: Name of module used

        **Example request**

        .. sourcecode:: http

            GET /api/v0.1/process/12345
            Host: localhost
            Accept: application/json

        **Example response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "process_id": 12345,
                "running": true
            }

        """

        try:
            thread = threads[process_id]
        except KeyError:
            return {"message": "%s did not exist" % process_id}, 404

        try:
            process_log, _ = thread["log"]
        except KeyError:
            process_log = []

        # parser = flask.ext.restful.reqparse.RequestParser()
        # parser.add_argument("index", type=int, default=0)

        # kwargs = parser.parse_args()

        index = 0
        last_index = min([len(process_log) - 1, 0])

        serialised_logs = []
        for record in process_log[index:]:
            serialised_logs.append(record.__dict__)

        formatted_errors = []
        for error in thread["errors"]:
            formatted = format_error(error)
            formatted_errors.append(formatted)

        return {"process_id": process_id,
                "running": thread["handle"].is_alive(),
                "messages": serialised_logs,
                "errors": formatted_errors,
                "lastIndex": last_index}, 200

    def put(self, process_id):
        """Modify a process

        :param process_id: Unique process identifier

        :>json bool ok: Operation status

        :status 200: Process was successfully modified

        """

        return {"ok": False, "process_id": process_id}, 501  # Not implemented

    def delete(self, process_id):
        """Remove process, including elements of process, from server

        This is ONLY used for memory-optimisations,
        server-side and has no impact the client.

        :param process_id: Unique process identifier

        :>json bool ok: Operation status, not returned upon error
        :>json string message: Error message

        :status 200: Process was successfully cleaned up
        :status 404: Process was not found

        """

        try:
            threads.pop(process_id)
        except KeyError:
            return {"message": "Process was not found"}, 404

        return {"ok": True}, 200


class ProcessesLogApi(flask.ext.restful.Resource):
    """Process log API

    GET /processes/<process_id/log

    """

    def get(self, process_id):
        """Get formatted log messages for process_id

        :query int index: From where to start returning messages
        :query string index: Python format string, e.g.
            '%(level)s %(message)s'

        :>jsonarr string message: Logged message
        :>jsonarr int lastIndex: Index of last message

        :status 200: Log messages returned
        :status 404: process_id was not found

        """

        parser = flask.ext.restful.reqparse.RequestParser()
        parser.add_argument("format", default="%(asctime)s "
                                              "%(levelname)s "
                                              "%(message)s")
        parser.add_argument("index", type=int, default=0)

        kwargs = parser.parse_args()

        formatter = logging.Formatter(kwargs["format"])
        index = kwargs["index"]

        messages = []

        try:
            process_log, process_handler = threads[process_id]["log"]
        except KeyError:
            return messages, 404

        last_index = len(process_log)
        for record in process_log[index:last_index]:
            message = formatter.format(record)
            messages.append(message)

        response = {
            "lastIndex": last_index,
            "messages": messages
        }

        return response, 200


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
