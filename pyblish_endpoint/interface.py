
# Standard library
import json

# Dependencies
import flask.ext.restful

# Local library
import service


def loads(data):
    """Load JSON as string instead of unicode objects
    Arguments:
        data (str): String of JSON data
    """

    return convert(json.loads(data))


def convert(input):
    """Cast input to string
    Arguments:
        input (object): Dict, list or unicode object to be converted
    """

    if isinstance(input, dict):
        return dict((convert(k), convert(v)) for k, v in input.iteritems())
    elif isinstance(input, list):
        return [convert(e) for e in input]
    elif isinstance(input, unicode):
        return input.encode("utf-8")
    else:
        return input


class Instance(flask.ext.restful.Resource):
    def get(self):
        """Return all available instances"""
        instances = service.current_service().instances()
        return instances


class Publish(flask.ext.restful.Resource):
    def post(self):
        data_str = flask.request.stream.read()
        data_json = loads(data_str)

        print data_json

        return service.current_service().publish()
