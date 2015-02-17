[![Build Status](https://travis-ci.org/pyblish/pyblish-endpoint.svg?branch=master)](https://travis-ci.org/pyblish/pyblish-endpoint)
[![PyPi](https://badge.fury.io/py/pyblish-endpoint.svg)](http://badge.fury.io/py/pyblish-endpoint)

![Pyblish Endpoint][logo]

An integration endpoint for externally running frontends of [Pyblish][pyblish].

- [What does it do?](https://github.com/pyblish/pyblish-endpoint/wiki/What-does-it-do%3F)

<br>
<br>
<br>

### Architecture

Pyblish Endpoint is a RESTful interface to Pyblish. It is built to facilitate inter-process communication of the various frontends supported by [Pyblish][pyblish].

Communication between a host and frontend occurs via this interface. In a nutshell, the communication looks something like this.

**High-Level Architecture**

![Endpoint Schematic][schematic]

The frontend sends requests to a host by first going through an endpoint.

However to fully encapsulate a frontend from implementation details of both Pyblish and host, there is the *service*.

**The Service**

![Endpoint Service][service]

The *service* acts as a layer inbetween a host and Endpoint so as to provide Endpoint with a common interface to Pyblish, relieving Endpoint from knowing about the internals of what has to happen in order for a host to perform the requested operations.

<br>
<br>
<br>

### Examples

For an example of an implemented frontend, head over to [Pyblish QML][qml], a frontend built with QML 5 of Qt. For an example of an implemented *service*, have a look at the one provided via [Pyblish for Maya][maya].

[qml]: https://github.com/pyblish/pyblish-qml
[maya]: https://github.com/pyblish/pyblish-maya/blob/master/pyblish_maya/service.py
[interface]: https://github.com/pyblish/pyblish-endpoint/blob/master/pyblish_endpoint/service.py#L22
[pyblish]: https://github.com/pyblish/pyblish
[schematic]: https://cloud.githubusercontent.com/assets/2152766/4996672/b61e3d06-69c0-11e4-88fb-236b2ccb26c6.png
[service]: https://cloud.githubusercontent.com/assets/2152766/4996259/519c11f2-69be-11e4-872d-a146ea132faf.png
[logo]: https://cloud.githubusercontent.com/assets/2152766/4995061/128ed178-69b6-11e4-99bf-586353d2b9be.png
