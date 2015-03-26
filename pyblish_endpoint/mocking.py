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

ConformAsset = type("ConformAsset", (pyblish.api.Conformer,), {})


@pyblish.api.log
class SelectInstances(pyblish.api.Selector):
    """Select debugging instances

    These instances are part of the evil plan to destroy the world.
    Be weary, be vigilant, be sexy.

    """

    hosts = ["python"]

    def process_context(self, context):
        self.log.info("Selecting instances..")

        for name in INSTANCES:
            instance = context.create_instance(name=name)

            self.log.info("Selecting: %s" % name)

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


class SelectInstancesFailure(pyblish.api.Selector):
    """Select some instances, but fail before adding anything to the context.

    That's right. I'm programmed to fail. Try me.

    """

    hosts = ["python"]

    def process_context(self, context):
        self.log.warning("I'm about to fail")
        raise pyblish.api.SelectionError("I was programmed to fail")


class SelectInstanceAndProcess(pyblish.api.Selector):
    """Select an instance, and also process it.

    Not sure why this would be necessary, but I'd imagine the need
    coming up eventually.

    If this plug-in isn't logging information about which instance
    it processes, something's wrong.

    """

    hosts = ["python"]
    families = ["napoleon.asset.rig"]

    def process_context(self, context):
        self.log.info("Selecting additional instance \"Extra1\"")
        instance = context.create_instance("Extra1")
        instance.set_data("family", "napoleon.asset.rig")

    def process_instance(self, instance):
        self.log.info("Processing my own instance: %s" % instance)


@pyblish.api.log
class ValidateNamespace(pyblish.api.Validator):
    """Namespaces must be orange

    In case a namespace is not orange, report immediately to
    your officer in charge, ask for a refund, do a backflip.

    This has been an example of:

    - A long doc-string
    - With a list
    - And plenty of newlines and tabs.

    """

    families = ["napoleon.animation.cache"]
    hosts = ["*"]
    version = (0, 0, 1)

    def process_instance(self, instance):
        self.log.info("Validating the namespace of %s" % instance.data("name"))
        self.log.info("""And here's another message, quite long, in fact it's too long to be displayed in a single row of text.
But that's how we roll down here. It's got \nnew lines\nas well.

- And lists
- And more lists

        """)


@pyblish.api.log
class ValidateContext(pyblish.api.Validator):
    def process_context(self, context):
        self.log.info("Processing context..")


@pyblish.api.log
class ValidateContextFailure(pyblish.api.Validator):
    def process_context(self, context):
        self.log.info("About to fail..")
        raise pyblish.api.ValidationError("""I was programmed to fail

The reason I failed was because the sun was not aligned with the tides,
and the moon is gray; not yellow. Try again when the moon is yellow.""")


@pyblish.api.log
class Validator1(pyblish.api.Validator):
    """Test of the order attribute"""
    order = pyblish.api.Validator.order + 0.1

    def process_instance(self, instance):
        pass


@pyblish.api.log
class Validator2(pyblish.api.Validator):
    order = pyblish.api.Validator.order + 0.2

    def process_instance(self, instance):
        pass


@pyblish.api.log
class Validator3(pyblish.api.Validator):
    order = pyblish.api.Validator.order + 0.3

    def process_instance(self, instance):
        pass


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
            self.log.debug("e = mc^2")
            self.log.info("About to fail..")
            self.log.warning("Failing.. soooon..")
            self.log.critical("Ok, you're done.")
            raise ValueError("""ValidateFailureMock was destined to fail..

Here's some extended information about what went wrong.

It has quite the long string associated with it, including
a few newlines and a list.

- Item 1
- Item 2

""")


@pyblish.api.log
class ValidateIsIncompatible(pyblish.api.Validator):
    """This plug-in should never appear.."""
    hosts = ["*"]
    version = (0, 0, 1)
    optional = True


@pyblish.api.log
class ExtractAsMa(pyblish.api.Extractor):
    """Extract contents of each instance into .ma

    Serialise scene using Maya's own facilities and then put
    it on the hard-disk. Once complete, this plug-in relies
    on a Conformer to put it in it's final location, as this
    extractor merely positions it in the users local temp-
    directory.

    """

    hosts = ["*"]
    version = (0, 0, 1)
    optional = True

    def process_instance(self, instance):
        self.log.info("About to extract scene to .ma..")
        self.log.info("Extraction went well, now verifying the data..")

        if instance.name == "Richard05":
            self.log.warning("You're almost running out of disk space!")

        self.log.info("About to finish up")
        self.log.info("Finished successfully")


INSTANCES = [
    "Peter01",
    "Richard05",
    "Steven11",
    "Piraya12",
    "Marcus"
]

PLUGINS = [
    SelectInstances,
    SelectInstancesFailure,
    SelectInstanceAndProcess,
    ExtractAsMa,
    ConformAsset,
    ValidateFailureMock,
    ValidateNamespace,
    ValidateIsIncompatible,
    ValidateContext,
    ValidateContextFailure,
    Validator1,
    Validator2,
    Validator3
]
