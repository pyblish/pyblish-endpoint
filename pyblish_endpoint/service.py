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
import warnings
import traceback

import pyblish
import pyblish.api

from version import version

log = logging.getLogger("endpoint")


class State(dict):
    """Hold on to information about host state

    State does not modify or interact with host and
    is therefore thread-safe.

    """

    def __init__(self, service):
        self.service = service

        self.current_plugin = None
        self.current_instance = None
        self.current_error = None
        self.current_records = None

        self.next_plugin = None
        self.next_instance = None

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
            "context": self.service.context,

            "current_plugin": self.current_plugin,
            "current_instance": self.current_instance,
            "current_error": self.current_plugin,
            "current_records": self.current_records,

            "next_plugin": self.next_plugin,
            "next_instance": self.next_instance,
        })

        super(State, self).update(state)

    def update(self, state):
        """Parse changes from `state` and apply to Service

        Given a dictionary of changes, apply changes to
        corresponding instances and plug-ins.

        For example, a plug-in may have been toggled off; an
        instance may have had it's data modified.

        Arguments:
            state (dict): Dictionary of changes.

        """

        # NOTE(marcus): Temporary
        self.current_plugin = None
        self.current_instance = None
        self.current_plugin = None
        self.current_records = None
        self.next_plugin = None
        self.next_instance = None

        s_context = state.get("context", {})
        s_plugins = state.get("plugins", [])

        # s_ prefix represents serialised data
        for s_instance in s_context.get("children", []):
            name = s_instance["name"]
            instance = self.service.instance_by_name(name)

            if not instance:
                log.error(
                    "Instance from client does "
                    "not exist on server: %s "
                    "(available instances: %s)"
                    % (name, [i.name for i in self.service.context]))
                continue

            changed_data = s_instance.get("data", {})

            for key, value in changed_data.iteritems():
                print(
                    "Changing \"{instance}.{data}\" from "
                    "\"{from_}\" to \"{to}\"".format(
                        instance=name,
                        data=key,
                        from_=instance.data(key),
                        to=value))

                instance.set_data(key, value)

        for s_plugin in s_plugins:
            name = s_plugin["name"]
            plugin = self.service.plugin_by_name(name)

            if not plugin:
                log.error(
                    "Plugin from client does "
                    "not exist on server: %s "
                    "(available plugins: %s"
                    % (name, [p.name for p in self.service.plugins]))
                continue

            changed_data = s_plugin.get("data", {})

            if changed_data:
                for key, value in changed_data.iteritems():
                    if key == "publish" and value is False:
                        print "Disabling %s" % plugin.__name__
                        plugin.flags = plugin.Disabled
                    else:
                        setattr(plugin, key, value)

    def clear(self):
        super(State, self).clear()
        self.current_plugin = None
        self.current_instance = None
        self.current_plugin = None
        self.current_records = None
        self.next_plugin = None
        self.next_instance = None


class EndpointService(object):
    """Abstract baseclass for host interfaces towards endpoint

    The Service is responsible for computing and fetching data
    from a host and is thus *not* thread-safe.

    """

    _current = None

    def __init__(self):
        self.context = None
        self.plugins = None
        self.processor = None

        self.state = State(self)

    def init(self):
        """Create context and discover plug-ins and instances"""
        self.reset()

        context = pyblish.api.Context()
        plugins = pyblish.api.discover()

        log.info("Performing selection..")
        for plugin in list(plugins):
            if not issubclass(plugin, pyblish.api.Selector):
                continue

            log.info("Processing %s" % plugin)
            for inst, err in plugin().process(context):
                pass

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

            context.set_data(key, value)

        self.context = context
        self.plugins = plugins

    def reset(self):
        self.context = None
        self.plugins = None
        self.processor = None
        self.state.clear()

    def system(self):
        warnings.warn("system() deprecated")
        return {}

    def versions(self):
        warnings.warn("versions() deprecated")
        return {}

    def next(self):
        warnings.warn("next() deprecated; use advance()")
        return self.advance()

    def advance(self):
        """Process current plug-in and advance state"""

        records = list()
        handler = MessageHandler(records)

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        if self.processor is None:
            self.processor = processor(self)

        try:
            self.processor.next()

            formatted_records = list()
            for record in records:
                formatted_records.append(format_record(record))

            if self.state.current_error is not None:
                formatted_error = format_error(self.state.current_error)
            else:
                formatted_error = None

            return {
                "current_plugin": self.state.current_plugin,
                "current_instance": self.state.current_instance,
                "next_plugin": self.state.next_plugin,
                "next_instance": self.state.next_instance,
                "error": formatted_error,
                "records": formatted_records
            }

        except StopIteration:
            self.processor = None
            return False

        finally:
            root_logger.removeHandler(handler)

    def plugin_by_name(self, name):
        """Return plugin by `name`

        Attributes:
            name (str): Name of plug-in

        """

        by_name = dict()
        for plugin in self.plugins:
            by_name[plugin.__name__] = plugin
        return by_name.get(name)

    def plugin_by_index(self, index):
        """Return plug-in by `index`

        Attributes:
            index (int): Index of plug-in

        """

        return self.plugins[index]

    def instance_by_index(self, index):
        """Return instance by `index`

        Attributes:
            index (int): Index of instance

        """

        return self.context[index]

    def instance_by_name(self, name):
        """Return instance by `name`

        Attributes:
            name (str): Name of instance

        """

        by_name = dict()
        for instance in self.context:
            by_name[instance.data("name")] = instance
        return by_name.get(name)


def processor(obj):
    """Publishing processor

    Given a service, provide for an iterator to advance
    it's current state; modifying state as it goes.

    Attributes:
        obj (EndpointService): Service to process

    """

    if not obj.plugins:
        raise StopIteration("No plug-ins for processor")

    for plugin in obj.plugins:

        if plugin.flags & plugin.Disabled:
            print "Skipping %s; disabled" % plugin
            continue

        try:
            next_index = obj.plugins.index(plugin) + 1
            next_plugin = obj.context[next_index]

            while next_plugin.data("publish") is False:
                next_index += 1
                next_plugin = obj.plugins[next_index]

            next_plugin = next_plugin.data("name")

        except IndexError:
            next_plugin = None

        obj.state.current_plugin = plugin.__name__
        obj.state.next_plugin = next_plugin

        print "Next plugin: %s" % next_plugin

        for instance, error in plugin().process(obj.context):
            try:
                current_instance = instance.data("name")

            except:
                # Context processed, not instance
                current_instance = None

            try:
                next_index = obj.context.index(instance) + 1
                next_instance = obj.context[next_index]

                while next_instance.data("publish") is False:
                    next_index += 1
                    next_instance = obj.context[next_index]

                next_instance = next_instance.data("name")

            except IndexError:
                next_instance = None

            print "Next instance: %s" % next_instance

            try:
                _, _, exc_tb = sys.exc_info()
                error.traceback = traceback.extract_tb(
                    exc_tb)[-1]
            except:
                pass

            obj.state.current_instance = current_instance
            obj.state.next_instance = next_instance
            obj.state.current_error = error

            yield


class MessageHandler(logging.Handler):
    def __init__(self, records, *args, **kwargs):
        # Not using super(), for compatibility with Python 2.6
        logging.Handler.__init__(self, *args, **kwargs)

        self.records = records

    def emit(self, record):
        # Do not record server messages
        if record.name in ["werkzeug"]:
            return

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
    try:
        formatted = {
            "context": format_context(state["context"]),
            "plugins": format_plugins(
                state["plugins"],
                data={"context": state["context"]}),

            "current_instance": state["current_instance"],
            "current_plugin": state["current_plugin"],

            "next_plugin": state["next_plugin"],
            "next_instance": state["next_instance"],
        }

    except Exception as e:
        _, _, exc_tb = sys.exc_info()
        e.traceback = traceback.extract_tb(exc_tb)[-1]

        message = """{message}

Filename: {fname}
Line: {line_number}
Function: {func}
Exc: {exc}
""".format(**format_error(e))

        formatted = {"error": message}

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
        objName (str, optional): Name of physical object
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
        "name": instance.data("name"),
        "family": instance.data("family"),
        "objName": instance.name,
        "children": children,
        "data": data,
        "publish": instance.data("publish"),
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

    """

    formatted = {
        "name": plugin.__name__,
        "version": plugin.version,
        "category": getattr(plugin, "category", None),
        "requires": plugin.requires,
        "order": plugin.order,
        "optional": plugin.optional,
        "doc": getattr(plugin, "doc", plugin.__doc__),
        "hasRepair": hasattr(plugin, "repair_instance"),
        "hasCompatible": False
    }

    # Make decisions based on provided `data`
    if data:
        if data.get("context"):
            if hasattr(plugin, "families"):
                if pyblish.api.instances_by_plugin(
                        data.get("context"), plugin):
                    formatted["hasCompatible"] = True

    try:
        # The MRO is as follows: (-1)object, (-2)Plugin, (-3)Selector..
        formatted["type"] = plugin.__mro__[-3].__name__
    except IndexError:
        # Plug-in was not subclasses from any of the
        # provided superclasses of pyblish.api. This
        # is either a bug or some (very) custom behavior
        # on the users part.
        log.critical("This is a bug")
        formatted["type"] = "Unknown"

    for attr in ("hosts", "families"):
        if hasattr(plugin, attr):
            formatted[attr] = getattr(plugin, attr)

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
