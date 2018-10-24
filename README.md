# influxstats

Create consistent stats across your entire codebase.

The `influxstats` module names each stat according to the function name and module path, and provides a base set of
default metrics.  Take the following code snippet for a function in a module `mypackage.utils`:

```python
import statsd


def make_request(url):
    """
    Returns content for the given url
    """
    with statsd.timer('request_time'):
      response = requests.get()
      content = response.content

    return content
```

In the above snippet, you will have a stat named `request_time`, but you will not know where in the code that came
from.  Take the same code snippet using influxstats:

```python
from mypackage.metrics import get_client

METRICS = get_client(__name__)

@METRICS.measure_function()
def make_request(url):
    """
    Returns content for the given url
    """
    response = requests.get()
    content = response.content

    return content
```

The above code will not only produce a timer as in the first snippet, but you will also get an increment to know how
many times the function was called as well as consistent naming.  Using influxdb's tags, the metric will be tagged with:

- module: the module path, i.e. mypackage.utils
- class: the class the function lives in (if applicable)
- def: the function name

It's also possible to emit additional stats within your functions by including an optional `statsd` kwarg:

```python
@METRICS.measure_function()
def make_request(url, statsd=None):
  statsd.incr('another_metric')
  [...]
```

The easiest way to use influxstats is to wrap it with your custom `get_client()` function, which can look similar to:

```python
"""
metrics helper module
"""
from influxstats import metrics


def get_client(module_path, tags=None):
    """
    Returns a Stats client for the given module path

    Args:
        module_path (str): the module this client is being instantiated from
        tags (dict): additional tags to add to the client

    Returns:
        metrics.StatsdClient
    """
    host = 'your statsd hostname'
    port = <your statsd port number>

    service = '<name of your application>'

    return metrics.get_client(service, module_path, tags=tags, host=host, port=port)
```
