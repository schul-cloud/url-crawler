import pytest
from bottle import Bottle, ServerAdapter
from threading import Thread
from schul_cloud_resources_api_v1.schema import get_valid_examples
from schul_cloud_resources_api_v1 import ApiClient, ResourceApi
from schul_cloud_resources_server_tests.app import run as run_test_server_app
from schul_cloud_resources_server_tests.tests.fixtures import *
from schul_cloud_url_crawler import ResourceClient, CrawledResource
import time
import requests


# configuration
NUMBER_OF_VALID_RESOURCES = 3
STARTUP_TIMEOUT = 2 # seconds

# module constants
VALID_RESOURCES = get_valid_examples()


@pytest.fixture(scope="session")
def host():
    """The host of the application."""
    return "localhost"


@pytest.fixture(scope="session")
def _server():
    """The server to start the app."""
    return StoppableWSGIRefServerAdapter()


@pytest.fixture(scope="session")
def app(_server, host):
    """The bottle app serving the resources."""
    app = Bottle()
    # app.run http://bottlepy.org/docs/dev/api.html#bottle.run
    thread = Thread(target=app.run, kwargs=dict(host=host, server=_server))
    thread.start()
    while not _server.get_port(): time.sleep(0.001)
    yield app
    # app.close http://bottlepy.org/docs/dev/api.html#bottle.Bottle.close
    app.close()
    _server.shutdown()
    thread.join()


@pytest.fixture
def port(_server, app):
    """The port of the application running."""
    return _server.get_port()


@pytest.fixture
def base_url(host, port):
    """The http url to the server for resources.

    The server is not started.
    """
    return "http://{}:{}".format(host, port)


@pytest.fixture
def serve(app, base_url):
    """A function to serve resources."""
    served = []
    def serve(body):
        """Serve a response body and return the url."""
        url = "/crawled-server/" + str(len(served)) 
        served.append(url)
        app.get(url, callback=lambda: body)
        return base_url + url
    yield serve
    app.reset()


_resource_id = 0

def resource_with_id(resource):
    """Set the id for a resource."""
    global _resource_id
    _resource_id += 1
    resource = resource.copy()
    assert "X-Test-Id" not in resource
    resource["X-Test-Id"] = _resource_id
    return resource

@pytest.fixture(params=VALID_RESOURCES[:NUMBER_OF_VALID_RESOURCES])
def resource(request):
    """A valid resource."""
    return resource_with_id(request.param)


@pytest.fixture
def resource_url(resource, serve):
    """The url to retrieve the valid resource."""
    return serve(resource)


@pytest.fixture(params=[
    ["http://asdasd.asd"],
    ["http://asdasd.asd", "http://asdasd.asd#4", "http://asdasd.asd2#44"],
    ["https://wikipedia.de/w/batman", "https://wikipedia.de/w/media/batman.png"]])
def resource_path(request):
    """A list of urls where the resources originates from."""
    return request.param


@pytest.fixture(params=[
        VALID_RESOURCES,       # all valid resources
        [VALID_RESOURCES[0]],  # one valid resource
        VALID_RESOURCES[::-2], # every second resource in reversed order
        []                       # no resources
    ])
def resources(request):
    """A list of resources."""
    return list(map(resource_with_id, request.param))


@pytest.fixture
def resource_urls(resources, serve):
    """The list of orls where the resources can be found."""
    return [serve(resource) for resource in resources]

@pytest.fixture
def resource_urls_url(resource_urls, serve):
    """Serve a list of urls."""
    return serve("\n".join(resource_urls))

# TODO: add fixture for authentication

@pytest.fixture
def client(resources_server):
    """Return a ResourceClient."""
    return ResourceClient(resources_server.url)


@pytest.fixture
def crawled_resource(resource, resource_path):
    """Return a crawled resource."""
    return CrawledResource(resource, resource_path)

