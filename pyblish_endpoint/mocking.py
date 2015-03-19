import time
import logging

import pyblish.api

import service


log = logging.getLogger("endpoint")


class MockService(service.EndpointService):
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
        self.reset()

        for plugin in PLUGINS:
            plugin.families = ["napoleon.animation.cache"]

            if plugin.__name__ == "ConformAsset":
                plugin.families = ["napoleon.asset.rig"]

            if plugin == ValidateIsIncompatible:
                plugin.families = ["napoleon.incompatible"]

            plugin.hosts = ["python"]

            self.plugins.append(plugin)

        for name in INSTANCES:
            instance = self.context.create_instance(name=name)

            instance._data = {
                "publish": True,
                "family": "napoleon.animation.cache",
                "identifier": "napoleon.instance",
                "minWidth": 800,
                "assetSource": "/server/assets/Peter",
                "destination": "/server/published/assets",
            }

            if name == "Peter01":
                instance.set_data("publish", False)
                instance.set_data("family", "napoleon.asset.rig")
            # else:
            #     instance.set_data("family", "napoleon.animation.cache")

            for node in ["node1", "node2", "node3"]:
                instance.append(node)

        pyblish.api.sort_plugins(self.plugins)

    def process(self, *args, **kwargs):
        result = super(MockService, self).process(*args, **kwargs)
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


#
# Test plug-ins
#

ExtractAsMa = type("ExtractAsMa", (pyblish.api.Extractor,), {})
ConformAsset = type("ConformAsset", (pyblish.api.Conformer,), {})


@pyblish.api.log
class ValidateNamespace(pyblish.api.Validator):
    """Validate the namespaces, or else"""
    families = ["napoleon.animation.cache"]
    hosts = ["*"]
    version = (0, 0, 1)

    def process_instance(self, instance):
        self.log.info("Validating the namespace of %s" % instance.data("name"))


@pyblish.api.log
class ValidateFailureMock(pyblish.api.Validator):
    """Plug-in that always fails"""
    families = ["*"]
    hosts = ["*"]
    version = (0, 0, 1)
    optional = True
    order = pyblish.api.Validator.order + 0.1

    def process_instance(self, instance):
        if instance.name == "Richard05":
            self.log.info("About to fail..")
            raise ValueError("ValidateFailureMock was destined to fail")


@pyblish.api.log
class ValidateIsIncompatible(pyblish.api.Validator):
    """This plug-in should never appear.."""
    hosts = ["*"]
    version = (0, 0, 1)
    optional = True


INSTANCES = ["Peter01",
             "Richard05",
             "Steven11",
             "Piraya12",
             "Marcus"]
PLUGINS = [
    ExtractAsMa,
    ConformAsset,
    ValidateFailureMock,
    ValidateNamespace,
    ValidateIsIncompatible
]
