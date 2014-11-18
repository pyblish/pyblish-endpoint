import logging
from pyblish_endpoint import server, resource, service

resource.setup_message_queue()

server.app.config["TESTING"] = True
app = server.app.test_client()
app.testing = True

log = logging.getLogger("endpoint")


instances = {
    "Peter01": {
        "family": "napoleon.asset.rig",
        "nodes": [
            {"name": "node1"},
            {"name": "node2"},
            {"name": "node3"}
        ],
        "data": {
            "identifier": "napoleon.instance",
            "minWidth": 800,
            "assetSource": "/server/assets/Peter",
            "destination": "/server/published/assets"
        }
    }
}


class EndpointService(service.EndpointService):
    def instances(self):
        instances = [
            {
                "name": "Peter01",
                "objName": "Peter01:pointcache_SEL",
                "family": "napoleon.asset.rig"
            },
            {
                "name": "Richard05",
                "objName": "Richard05:pointcache_SEL",
                "family": "napoleon.animation.rig"
            }
        ]

        return instances

    def instance_data(self, instance_id):
        instance = instances[instance_id]
        return instance.get("data")

    def instance_nodes(self, instance_id):
        instance = instances[instance_id]
        return instance.get("nodes")

    def process(self, instance, plugin):
        log.info("Running first pass..")
        log.info("Almost done..")
        log.info("Completed successfully!")

        return True


service.register_service(EndpointService, force=True)
