import pyblish.api

from .. import service


class TestService(service.EndpointService):
    """Service for testing

    Attributes:
        SLEEP_DURATION: Fake processing delay, in milliseconds
        NUM_INSTANCES: Fake amount of available instances (max: 2)
        PERFORMANCE: Enum of fake performance. Available values are
            SLOW, MODERATE, FAST, NATIVE

    """

    def init(self):
        self.plugins = []
        for plugin in PLUGINS:
            plugin.families = ["napoleon.animation.cache"]
            if plugin == "ConformAsset":
                plugin.families = ["napoleon.asset.rig"]

            plugin.hosts = ["python", "maya"]
            self.plugins.append(plugin)

        self.plugins.append(ValidateFailureMock)
        self.plugins.append(ValidateNamespace)
        self.plugins = self.sort_plugins(self.plugins)

        context = pyblish.api.Context()
        for name in INSTANCES:
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


#
# Test plug-ins
#

ExtractAsMa = type("ExtractAsMa", (pyblish.api.Extractor,), {})
ConformAsset = type("ConformAsset", (pyblish.api.Conformer,), {})


@pyblish.api.log
class ValidateNamespace(pyblish.api.Validator):
    families = ["napoleon.animation.cache"]
    hosts = ["*"]
    version = (0, 0, 1)

    def process_instance(self, instance):
        self.log.info("Validating namespace..")
        self.log.info("Completed validating namespace!")


@pyblish.api.log
class ValidateFailureMock(pyblish.api.Validator):
    families = ["*"]
    hosts = ["*"]
    version = (0, 0, 1)
    optional = True

    def process_instance(self, instance):
        raise ValueError("Instance failed")


INSTANCES = ["Peter01", "Richard05", "Steven11", "Piraya12", "Marcus"]
PLUGINS = [ExtractAsMa, ConformAsset, ValidateFailureMock, ValidateNamespace]
