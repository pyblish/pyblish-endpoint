"""Endpoint resources

Attributes:
    log: Current logger
    request_queue: Cache of requests for
        long-polling; see Client.

"""

# Standard library
import sys
import json
import Queue
import logging
import traceback

# Dependencies
import flask.ext.restful
import flask.ext.restful.reqparse

# Local library
import schema
import service as service_mod

log = logging.getLogger("endpoint")
request_queue = Queue.Queue()


class ClientApi(flask.ext.restful.Resource):
    """Client API

    Send requests from server to client.
    A heartbeat is emitted once every second.

    GET /client
    POST /client

    """

    def get(self):
        dequeue = [str(item) for item in request_queue.queue]
        return {"ok": True, "queue": dequeue}, 200

    def post(self):
        try:
            message = request_queue.get(timeout=1)
        except Queue.Empty:
            return {"ok": True, "message": "heartbeat"}, 200

        return {"ok": True, "message": message}, 200


class StateApi(flask.ext.restful.Resource):
    """State API between host and client

    GET /state
    POST /state
    PUT /state
    DELETE /state

    """

    def get(self):
        """Return state; do not modify

        :>jsonarr array context: Context, incl. data and children
        :>jsonarr array plugins: Available plug-ins

        :status 200: Return state as per schema_state.json

        """

        state = service_mod.current().state

        try:
            state.compute()
            schema.validate(state, schema="state")

        except schema.ValidationError as e:
            return {"ok": False, "message": str(e)}, 500

        except Exception as e:
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                message = "".join(traceback.format_exception(
                    exc_type, exc_value, exc_traceback))
            except:
                message = str(e)

            return {"ok": False, "message": message}, 500

        return {"ok": True, "state": state}, 200

    def put(self):
        """Process plug-in

        :<json string plugin: Plug-in to process
        :<json string instance: Instance to process

        :>jsonarr string ok: Status message
        :>jsonarr Result result: Result dictionary; see schema for Result

        :status 200: Advance ok
        :status 400: Invalid arguments specified

        """
        parser = flask.ext.restful.reqparse.RequestParser()
        parser.add_argument("plugin", required=True, type=str)
        parser.add_argument("instance", type=str)

        kwargs = parser.parse_args()

        plugin = kwargs["plugin"]
        instance = kwargs["instance"]

        service = service_mod.current()

        try:
            result = service.process(plugin, instance)
            schema.validate(result, schema="result")

        except schema.ValidationError as e:
            return {"ok": False, "message": str(e)}, 500

        except Exception as e:
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                message = "".join(traceback.format_exception(
                    exc_type, exc_value, exc_traceback))
            except:
                message = str(e)
            return {"ok": False, "message": message}, 500

        return {"ok": True, "result": result}, 200

    def post(self):
        """Update state

        Given a `state`, update the host. Else re-evaluate
        current state of host and return it.

        :<jsonarr array state: Changes from client
        :>jsonarr array state: Applied changes
        :>jsonarr string message: Error message when status == 500
        :>jsonarr Changes changes: Changes dictionary; see schema for Changes

        :status 200: State returned
        :status 400: Invalid arguments specified
        :status 500: Internal error; see `message` for information.

        """

        parser = flask.ext.restful.reqparse.RequestParser()
        parser.add_argument("changes", type=str)

        kwargs = parser.parse_args()
        service = service_mod.current()

        if kwargs["changes"] is None:
            service.init()

        else:
            try:
                changes = json.loads(kwargs["changes"])
                schema.validate(changes, schema="changes")
                service.state.update(changes)

            except schema.ValidationError as e:
                return {"ok": False, "message": str(e)}, 500

            except ValueError:
                message = "Could not de-serialise state: %r" % kwargs
                log.error(message)
                return {"ok": False, "message": message}, 500

            except Exception as e:
                try:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    message = "".join(traceback.format_exception(
                        exc_type, exc_value, exc_traceback))
                except:
                    message = str(e)

                log.error(message)
                return {"ok": False, "message": str(message)}, 500

            return {"ok": True, "changes": changes}, 200

        return {"ok": True}, 200

    def delete(self):
        """Delete state

        Clears the current state; must POST to re-initialise.

        :>json bool ok: Status message

        :status 200: State deleted successfully
        :status 500: Internal error

        """

        try:
            service_mod.current().reset()

        except Exception as e:
            return {"ok": False, "message": str(e)}, 500

        return {"ok": True}, 200
