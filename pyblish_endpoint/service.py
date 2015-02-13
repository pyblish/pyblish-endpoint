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

        return True

    def sort_plugins(self, plugins):
        sorted_plugins = list()
        for type in (pyblish.api.Selector,
                     pyblish.api.Validator,
                     pyblish.api.Extractor,
                     pyblish.api.Conformer):
            for plugin in plugins:
                if issubclass(plugin, type):
                    sorted_plugins.append(plugin)

        for plugin in plugins:
            assert plugin in sorted_plugins

        return sorted_plugins

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
            # Build context from state
            context = pyblish.api.Context()
            context._data = self.context._data.copy()
            plugins = list()

            plugins_by_name = dict((p.__name__, p) for p in self.plugins)
            instances_by_name = dict((i.data("name"), i) for i in self.context)

            for plugin in self.state["plugins"]:
                obj = plugins_by_name.get(plugin)
                if obj is not None:
                    plugins.append(obj)
                else:
                    log.error("Plugin from client does "
                              "not exist on server: %s "
                              "(available plugins: %s"
                              % (plugin, self.plugins))

            for instance in self.state["context"]:
                obj = instances_by_name.get(instance)
                if obj is not None:
                    context.add(obj)
                else:
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


class MockService(EndpointService):
    """Service for testing

    Attributes:
        SLEEP_DURATION: Fake processing delay, in milliseconds
        NUM_INSTANCES: Fake amount of available instances (max: 2)
        PERFORMANCE: Enum of fake performance. Available values are
            SLOW, MODERATE, FAST, NATIVE

    """

    SLEEP_DURATION = 0
    NUM_INSTANCES = 3

    SLOW = 1 << 0
    MODERATE = 1 << 1
    FAST = 1 << 2
    NATIVE = 1 << 3
    PERFORMANCE = NATIVE

    def init(self):
        self.plugins = []
        for plugin, superclass in (
                ["ExtractAsMa", pyblish.api.Extractor],
                ["ConformAsset", pyblish.api.Conformer]):
            obj = type(plugin, (superclass,), {})

            obj.families = ["napoleon.animation.cache"]
            if plugin == "ConformAsset":
                obj.families = ["napoleon.asset.rig"]

            obj.hosts = ["python", "maya"]
            self.plugins.append(obj)

        self.plugins.append(ValidateFailureMock)
        self.plugins.append(ValidateNamespace)
        self.plugins = self.sort_plugins(self.plugins)

        fake_instances = ["Peter01", "Richard05", "Steven11"]
        context = pyblish.api.Context()
        for name in fake_instances[:self.NUM_INSTANCES]:
            instance = context.create_instance(name=name)

            instance._data = {
                "identifier": "napoleon.instance",
                "minWidth": 800,
                "assetSource": "/server/assets/Peter",
                "destination": "/server/published/assets",
            }

            instance.set_data("publish", True)

            if name == "Peter01":
                instance.set_data("publish", False)
                instance.set_data("family", "napoleon.asset.rig")
            else:
                instance.set_data("family", "napoleon.animation.cache")

            for node in ["node1", "node2", "node3"]:
                instance.append(node)

        self.context = context

    def process(self, instance, plugin):
        result = super(MockService, self).process(instance, plugin)
        self.sleep()
        return result

    def sleep(self):
        if self.SLEEP_DURATION:
            log.info("Pretending it takes %s seconds "
                     "to complete.." % self.SLEEP_DURATION)

            performance = self.SLEEP_DURATION
            if self.PERFORMANCE & self.SLOW:
                performance += 2

            if self.PERFORMANCE & self.MODERATE:
                performance += 1

            if self.PERFORMANCE & self.FAST:
                performance += 0.1

            if self.PERFORMANCE & self.NATIVE:
                performance = 0

            increment_sleep = performance / 3.0

            time.sleep(increment_sleep)
            log.info("Running first pass..")

            time.sleep(increment_sleep)
            log.info("Almost done..")

            time.sleep(increment_sleep)
            log.info("Completed successfully!")

    def process_state(self, state):
        for event in super(MockService, self).process_state(state):
            self.sleep()
            yield event


#
# Mock classes
#


class ValidateNamespace(pyblish.api.Validator):
    families = ["napoleon.animation.cache"]
    hosts = ["*"]
    version = (0, 0, 1)

    def process_instance(self, instance):
        log.info("Validating namespace..")
        log.info("Completed validating namespace!")


class ValidateFailureMock(pyblish.api.Validator):
    families = ["*"]
    hosts = ["*"]
    version = (0, 0, 1)
    optional = True

    def process_instance(self, instance):
        raise ValueError("Instance failed")

#
# End mock classes
#


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


def current_service():
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
