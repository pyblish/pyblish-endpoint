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
        for plugin, superclass in (
                ["ExtractAsMa", pyblish.api.Extractor],
                ["ConformAsset", pyblish.api.Conformer]):
            obj = type(plugin, (superclass,), {})

            obj.families = ["napoleon.animation.cache"]
            if plugin == "ConformAsset":
                obj.families = ["napoleon.asset.rig"]

            obj.hosts = ["python", "maya"]
            self.plugins.append(obj)

        self.plugins.append(service.ValidateFailureMock)
        self.plugins.append(service.ValidateNamespace)
        self.plugins = self.sort_plugins(self.plugins)

        fake_instances = ["Peter01", "Richard05", "Steven11"]
        context = pyblish.api.Context()
        for name in fake_instances:
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
