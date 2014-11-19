import logging
from pyblish_endpoint import server, resource, service

resource.setup_message_queue()

server.app.config["TESTING"] = True
app = server.app.test_client()
app.testing = True

log = logging.getLogger("endpoint")


service.register_service(service.MockService, force=True)
