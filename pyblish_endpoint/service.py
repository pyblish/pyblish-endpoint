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
import getpass
import logging

import pyblish
import pyblish.api

from version import version

log = logging.getLogger("endpoint")


class EndpointService(object):
    """Abstract baseclass for host interfaces towards endpoint"""

    _current = None

    def __init__(self):
        self.context = None
        self.plugins = None
        self.processor = None
        self.state = {
            "context": [],
            "plugins": []
        }

    def init(self):
        """Create context and discover plug-ins and instances"""

        context = pyblish.api.Context()
        plugins = pyblish.api.discover()

        log.debug("Performing selection..")
        for plugin in plugins:
            if not issubclass(plugin, pyblish.api.Selector):
                continue

            log.debug("Processing %s" % plugin)
            for inst, err in plugin().process(context):
                pass

        self.context = context
        self.plugins = self.sort_plugins(plugins)
        self.processor = None

        return True

    def sort_plugins(self, plugins):
        """Return `plugin` in order

        Their order is determined by their `order` attribute,
        which defaults to their standard execution order:

            1. Selection
            2. Validation
            3. Extraction
            4. Conform

        *But may be overridden.

        """

        return sorted(plugins, key=lambda p: p.order)

    def system(self):
        """Confirm connection and return system state"""

        executable = sys.executable
        basename = os.path.basename(executable)
        name, _ = os.path.splitext(basename)

        return {
            "host": name,
            "port": int(os.environ.get("ENDPOINT_PORT", -1)),
            "user": getpass.getuser(),
            "connectTime": time.time()
        }

    def versions(self):
        return {
            "pyblishVersion": pyblish.version,
            "endpointVersion": version,
            "pythonVersion": sys.version,
        }

    def next(self):
        """Process next plug-in in state"""

        if self.processor is None:
            context = pyblish.api.Context()
            context._data = self.context._data.copy()
            plugins = list()

            plugins_by_name = dict((p.__name__, p) for p in self.plugins)
            instances_by_name = dict((i.data("name"), i) for i in self.context)

            for plugin in self.state["plugins"]:
                try:
                    plugins.append(plugins_by_name[plugin])
                except KeyError:
                    log.error("Plugin from client does "
                              "not exist on server: %s "
                              "(available plugins: %s"
                              % (plugin, self.plugins))

            for instance in self.state["context"]:
                try:
                    context.add(instances_by_name[instance])
                except KeyError:
                    log.error("Instance from client does "
                              "not exist on server: %s "
                              "(available instances: %s)"
                              % (instance, self.context))

            def process():
                for plugin in plugins:
                    for instance, error in plugin().process(context):
                        yield {"plugin": plugin,
                               "instance": instance,
                               "error": error}

            self.processor = process()

        records = list()
        handler = MessageHandler(records)

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        try:
            result = self.processor.next()
            result["records"] = records
            return result
        except StopIteration:
            self.processor = None
            return None
        finally:
            root_logger.removeHandler(handler)


class MessageHandler(logging.Handler):
    def __init__(self, records, *args, **kwargs):
        # Not using super(), for compatibility with Python 2.6
        logging.Handler.__init__(self, *args, **kwargs)

        self.records = records

    def emit(self, record):
        # Do not record server messages
        if record.name in ["werkzeug"]:
            return

        self.records.append(record)


def current():
    """Return currently active service"""
    return EndpointService._current


def register_service(service, force=False):
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
