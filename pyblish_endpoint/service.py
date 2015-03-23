# *-* coding:utf-8*-*
"""Endpoint Service

In order to protect Endpoint from the internals or both Pyblish
and each host application, the service acts as a layer inbetween
the two.

Users are encouraged to subclass :class:`EndpointService` and
implement a minimum amount of features along with optionals.

Mandatory features are marked as being abstractmethods, whereas
optional features are not.

Optional features are, as the name implies, not necessary for
overall operation but may provide additional feedback or features
to users.

"""

import os
import sys
import time
import json
import getpass
import logging

import pyblish
import pyblish.api
import pyblish.plugin

from version import version

log = logging.getLogger("endpoint")


class State(dict):
    """Hold on to information about host state

    State does not modify or interact with host and
    is therefore thread-safe.

    """

    def __init__(self, service):
        self.service = service

    def compute(self):
        """Format current state of Service into JSON-compatible dictionary

        Given that the Service contains an up-to-date view of the host,
        format this information into a dictionary capable of being passed
        on to the client.

        Returns:
            state: JSON-compatible dictionary of current state

        """

        self.clear()

        state = format_state({
            "plugins": self.service.plugins,
            "context": self.service.context
        })

        super(State, self).update(state)

    def update(self, changes):
        """Parse changes from `changes` and apply to Service

        Given a dictionary of changes, apply changes to
        corresponding instances and plug-ins.

        Arguments:
            changes (dict): Dictionary of changes.

        """

        context_changes = changes["context"]

        for name, changes in context_changes.iteritems():

            try:
                instance = self.service.context[name]
            except KeyError:
                log.error(
                    "Instance from client does "
                    "not exist on server: %s "
                    "(available instances: %s)"
                    % (name, [i.name for i in self.service.context]))
                continue

            for key, change in changes.iteritems():
                current_value = instance.data(key)

                if current_value == change["new"]:
                    continue

                print(
                    "Changing \"{instance}.{data}\" from "
                    "\"{from_}\" to \"{to}\"".format(
                        instance=name,
                        data=key,
                        from_=instance.data(key),
                        to=change["new"]))

                instance.set_data(key, change["new"])


class Plugins(list):
    def __getitem__(self, index):
        if isinstance(index, int):
            return super(Plugins, self).__getitem__(index)

        for item in self:
            if item.__name__ == index:
                return item

        raise KeyError("%s not in list" % index)


class Context(pyblish.api.Context):
    def __getitem__(self, index):
        if isinstance(index, int):
            return super(Plugins, self).__getitem__(index)

        for item in self:
            if item.name == index:
                return item

        raise KeyError("%s not in list" % index)


class EndpointService(object):
    """Abstract baseclass for host interfaces towards endpoint

    The Service is responsible for computing and fetching data
    from a host and is thus *not* thread-safe.

    """

    _current = None

    def __init__(self):
        self.context = Context()
        self.plugins = Plugins()

        self.state = State(self)

    def init(self):
        """Create context and discover plug-ins and instances"""
        self.reset()

        self.plugins[:] = pyblish.api.discover()

        log.info("Performing selection..")
        for plugin in self.plugins:

            if not issubclass(plugin, pyblish.api.Selector):
                continue

            log.info("Processing %s" % plugin)
            for inst, err in plugin().process(self.context):
                pass

    def reset(self):
        self.context = Context()
        self.plugins = Plugins()
        self.state.clear()

        # Append additional metadata to context
        executable = sys.executable
        basename = os.path.basename(executable)
        name, _ = os.path.splitext(basename)

        for key, value in {"host": name,
                           "port": int(os.environ.get("ENDPOINT_PORT", -1)),
                           "user": getpass.getuser(),
                           "connectTime": time.time(),
                           "pyblishVersion": pyblish.version,
                           "endpointVersion": version,
                           "pythonVersion": sys.version}.iteritems():

            self.context.set_data(key, value)

    def process(self, plugin, instance):
        """Process `instance` with `plugin`

        Arguments:
            plugin (str): Id of plug-in to process
            instance (str): Id of instance to process

        """

        records = list()
        handler = MessageHandler(records)

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        Plugin = self.plugins[plugin]

        __count = 0
        __time = time.time()
        success = True
        o_instance = None
        formatted_error = None
        for o_instance, error in Plugin().process(self.context,
                                                  instances=[instance]):
            if error is not None:
                success = False
                formatted_error = format_error(error)

            __count += 1

        assert (o_instance.name == instance) if o_instance else True
        assert __count <= 2, "Processed more than two items: %i" % __count

        formatted_records = list()
        for record in records:
            formatted_records.append(format_record(record))

        return {
            "success": success,
            "plugin": plugin,
            "instance": instance or "Context",
            "error": formatted_error,
            "records": formatted_records,
            "duration": time.time() - __time
        }


class MessageHandler(logging.Handler):
    def __init__(self, records, *args, **kwargs):
        # Not using super(), for compatibility with Python 2.6
        logging.Handler.__init__(self, *args, **kwargs)

        self.records = records

    def emit(self, record):
        # Do not record server messages
        # if record.name in ["werkzeug"]:
        #     return

        if record.levelno < logging.INFO:
            return

        self.records.append(record)


def format_record(record):
    """Serialise LogRecord instance"""
    return record.__dict__


def format_error(error):
    """Serialise exception"""
    formatted = {"message": str(error)}

    if hasattr(error, "traceback"):
        fname, line_no, func, exc = error.traceback
        formatted.update({
            "fname": fname,
            "line_number": line_no,
            "func": func,
            "exc": exc
        })

    return formatted


def format_state(state):
    formatted = {
        "context": format_context(state["context"]),
        "plugins": format_plugins(
            state["plugins"],
            data={"context": state["context"]})
    }

    return formatted


def format_data(data):
    """Serialise instance/context data

    Given an arbitrary dictionary of Python object,
    return a JSON-compatible dictionary.

    Note that all keys are cast to string and that values
    not compatible with JSON are replaced with "Not supported".

    Arguments:
        data (dict): Data to serialise

    Returns:
        data (dict): Serialised data

    """

    formatted = dict()

    for key, value in data.iteritems():
        try:
            key = str(key)
        except:
            continue

        try:
            json.dumps(value)
        except:
            value = "Not supported"

        formatted[key] = value

    return formatted


def format_instance(instance, data=None):
    """Serialise `instance`

    For children to be visualised and modified,
    they must provide an appropriate implementation
    of __str__.

    Data that isn't JSON compatible cannot be
    visualised nor modified.

    Attributes:
        name (str): Name of instance
        niceName (str, optional): Nice name of instance
        family (str): Name of compatible family
        children (list, optional): Associated children
        data (dict, optional): Associated data
        publish (bool): Whether or not instance should be published

    Returns:
        Dictionary of JSON-compatible instance

    """

    children = list()
    for child in instance:
        try:
            json.dumps(child)
        except:
            child = "Invalid"
        children.append(child)

    data = format_data(instance._data)

    return {
        "name": instance.name,
        "children": children,
        "data": data
    }


def format_context(context, data=None):
    formatted = []

    for instance in context:
        formatted_instance = format_instance(instance, data)
        formatted.append(formatted_instance)

    return {
        "data": format_data(context._data),
        "children": formatted
    }


def format_plugins(plugins, data=None):
    """Serialise multiple plug-ins

    Returns:
        List of JSON-compatible plug-ins

    """

    formatted = []
    for plugin in plugins:
        formatted_plugin = format_plugin(plugin, data=data)
        formatted.append(formatted_plugin)

    return formatted


def format_plugin(plugin, data=None):
    """Serialise `plugin`

    Attributes:
        name: Name of Python class
        version: Plug-in version
        category: Optional category
        requires: Plug-in requirements
        order: Plug-in order
        optional: Is the plug-in optional?
        doc: The plug-in documentation
        hasRepair: Can the plug-in perform a repair?
        hasCompatible: Does the plug-in have any compatible instances?
        type: Which baseclass does the plug-in stem from? E.g. Validator
        module: File in which plug-in was defined

    """

    assert issubclass(plugin, pyblish.plugin.Plugin)

    formatted = {
        "name": plugin.__name__,
        "data": {
            "version": plugin.version,
            "category": getattr(plugin, "category", None),
            "requires": plugin.requires,
            "order": plugin.order,
            "optional": plugin.optional,
            "doc": getattr(plugin, "doc", plugin.__doc__),
            "hasRepair": hasattr(plugin, "repair_instance"),
            "hasCompatible": False,
            "hosts": [],
            "families": [],
            "type": None,
            "module": None
        }
    }

    # Make decisions based on provided `data`
    if data:
        if data.get("context"):
            if hasattr(plugin, "families"):
                if pyblish.api.instances_by_plugin(
                        data.get("context"), plugin):
                    formatted["data"]["hasCompatible"] = True

    try:
        # The MRO is as follows: (-1)object, (-2)Plugin, (-3)Selector..
        formatted["data"]["type"] = plugin.__mro__[-3].__name__
    except IndexError:
        # Plug-in was not subclasses from any of the
        # provided superclasses of pyblish.api. This
        # is either a bug or some (very) custom behavior
        # on the users part.
        log.critical("This is a bug")

    try:
        module = sys.modules[plugin.__module__]
        path = os.path.abspath(module.__file__)
        formatted["data"]["module"] = path
    except IndexError:
        pass

    for attr in ("hosts", "families"):
        if hasattr(plugin, attr):
            formatted["data"][attr] = getattr(plugin, attr)

    return formatted


def current():
    """Return currently active service"""
    return EndpointService._current


def register_service(service, force=True):
    """Register service

    The service will be used by the endpoint for host communication
    and represents a host-specific layer inbetween Pyblish and Endpoint.

    Arguments:
        service (EndpointService): Service to register
        force (bool): Overwrite any existing service

    """

    if EndpointService._current is not None and force is False:
        raise ValueError("An existing service was found: %s, "
                         "use deregister_service to remove it"
                         % type(EndpointService._current).__name__)
    EndpointService._current = service()
    log.info("Registering: %s" % service)


def deregister_service(service=None):
    if service is None or service is EndpointService._current:
        EndpointService._current = None
    else:
        raise ValueError("Could not deregister service")
