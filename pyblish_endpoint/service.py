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

    def init(self):
        log.debug("Computing context")
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
        self.plugins = plugins

        return True

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

    def process(self, instance, plugin):
        log.debug("Attempting to process %s with %s" % (instance, plugin))

        matches = filter(lambda p: p.__name__ == plugin, self.plugins)

        try:
            plugin = matches[0]
        except IndexError:
            raise ValueError("Plug-in: %s was not found" % plugin)

        for inst, err in plugin().process(self.context, instances=[instance]):
            log.info("Processing %s with %s" % (plugin, self.context))
            if err is not None:
                return err

        return True


class MockService(EndpointService):
    """Service for testing

    Attributes:
        SLEEP_DURATION: Fake processing delay, in milliseconds
        NUM_INSTANCES: Fake amount of available instances (max: 2)
        PERFORMANCE: Enum of fake performance. Available values are
            SLOW, MODERATE, FAST, NATIVE

    """

    SLEEP_DURATION = 0
    NUM_INSTANCES = 2

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

        context = pyblish.api.Context()
        for name in ("Peter01", "Richard05"):
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
        matches = filter(lambda p: p.__name__ == plugin, self.plugins)
        try:
            plugin = matches[0]
        except IndexError:
            raise ValueError("Plug-in: %s was not found" % plugin)

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

        for inst, err in plugin().process(self.context, instances=[instance]):
            log.info("Processing %s with %s" % (plugin, instance))
            log.info("inst: %s, err: %s" % (inst, err))
            if err is not None:
                return err

        return True


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
