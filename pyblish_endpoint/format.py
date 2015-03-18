class Changes(dict):
    """Data interchange format for changes

    Example:
        {
            "context": {
                "MyInstance": {
                    "startFrame": {
                        "new": 1001,
                        "old": 1000
                    },
                    "endFrame": {
                        "new": 1230,
                        "old": 1235
                    }
                },
                "MyOtherInstance": {
                    "endFrame": {
                        "new": 1210,
                        "old": 1235
                    }
                }
            },
            "plugins": {
                "ValidateNamespace": {
                    "families": {
                        "new": ["*"],
                        "old": ["something.else]
                    }
                }
            }
        }

    """

    _template = {
        "context": {
        },
        "plugins": {
        }
    }

    def __init__(self):
        self.update(self._template)

    def clear(self):
        super(Changes, self).clear()
        self.update(self._template)
