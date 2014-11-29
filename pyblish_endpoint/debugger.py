import requests
from PyQt5 import QtWidgets


class Window(QtWidgets.QWidget):
    template = "http://127.0.0.1:{port}/pyblish/v0.1{endpoint}"

    def __init__(self, port, parent=None):
        super(Window, self).__init__(parent)
        self.port = port

        body = QtWidgets.QWidget()
        sidebar = QtWidgets.QWidget()
        views = QtWidgets.QWidget()

        proc_view = QtWidgets.QListWidget()
        inst_view = QtWidgets.QListWidget()
        plug_view = QtWidgets.QListWidget()

        layout = QtWidgets.QVBoxLayout(sidebar)

        layout.addWidget(QtWidgets.QLabel("Actions"))

        refresh = QtWidgets.QPushButton("Refresh")
        refresh.pressed.connect(self.refresh)

        layout.addWidget(refresh)

        layout.addWidget(QtWidgets.QLabel("Process"))
        for name in ("ValidateNamingConvention",
                     "ExtractNapoleonAsMb",
                     "ConformNapoleonAsset"):
            button = QtWidgets.QPushButton(name)
            button.pressed.connect(
                lambda plugin=button.text(): self.process(plugin))
            layout.addWidget(button)

        layout.addWidget(QtWidgets.QLabel("GET"))

        for req in ("/instances",
                    "/instances/Diver"):
            button = QtWidgets.QPushButton(req)
            button.pressed.connect(
                lambda endpoint=button.text(): self.get(endpoint))
            layout.addWidget(button)

        layout = QtWidgets.QVBoxLayout(views)
        layout.addWidget(proc_view)
        layout.addWidget(inst_view)
        layout.addWidget(plug_view)

        layout = QtWidgets.QHBoxLayout(body)
        layout.addWidget(sidebar)
        layout.addWidget(views)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(body)

        self.proc_view = proc_view
        self.inst_view = inst_view
        self.plug_view = plug_view

        self.refresh()

    def refresh(self):
        res = requests.post(self.template.format(
            port=port,
            endpoint="/session"))

        if not res.status_code == 200:
            print res.json()
            return

        self.proc_view.clear()
        self.inst_view.clear()

        # Processes
        res = requests.get(self.template.format(
            port=self.port,
            endpoint="/processes"))

        processes = res.json()
        for process in processes:
            item = QtWidgets.QListWidgetItem(process["process_id"])
            self.proc_view.addItem(item)

        # Instances
        res = requests.get(self.template.format(
            port=self.port,
            endpoint="/instances"))

        instances = res.json()
        for instance in instances:
            item = QtWidgets.QListWidgetItem(instance["name"])
            self.inst_view.addItem(item)

        # Plug-ins
        res = requests.get(self.template.format(
            port=self.port,
            endpoint="/plugins"))

        plugins = res.json()
        print plugins
        for plugin in plugins:
            item = QtWidgets.QListWidgetItem(plugin["name"])
            self.inst_view.addItem(item)

    def get(self, endpoint):
        addr = self.template.format(
            port=self.port,
            endpoint=endpoint)

        print "Requesting %s" % addr
        res = requests.get(addr)
        print "Status: %s" % res.status_code
        print res.json()

    def process(self, plugin):
        addr = self.template.format(
            port=self.port,
            endpoint="/processes")

        print "Requesting %s" % addr
        res = requests.post(addr, data={"instance": "Diver",
                                        "plugin": plugin})
        print "Status: %s" % res.status_code
        print res.json()

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)

    port = sys.argv[1]

    win = Window(port)
    win.show()

    sys.exit(app.exec_())
