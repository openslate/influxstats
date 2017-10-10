# -*- coding: utf-8 -*-
"""
metrics helpers
"""
import contextlib
import functools
import hashlib
import json

import statsd

from statsd.client import StatsClientBase

# clients indexed by prefix
CLIENTS = {}


def get_cache_key(args, kwargs):
    """
    Returns a cache key from the given kwargs

    This is simply a sha256 hexdigest of the keyword arguments

    Args:
        kwargs (dict): the arguments to build a cache key from

    Returns:
        str: the cache key
    """
    sha = hashlib.sha256()
    sha.update(json.dumps([args, kwargs]).encode('utf8'))

    return sha.hexdigest()


def get_client(service, module, **kwargs):
    """
    Returns a StatsClient instance

    Args:
        service (str): name of the service this metric is coming from (aka: name of your app)
        module (str): __name__ within the context this is called from
        **kwargs: options passed directly to StatsClient

    Returns:
        StatsClient instance
    """
    cache_key = get_cache_key(module, kwargs)

    statsd_client = CLIENTS.get(cache_key)
    if statsd_client is None:
        tags = kwargs.pop('tags', {})
        tags.update({
            'module': module,
            'service': service,
        })

        statsd_client = StatsClient(tags=tags, **kwargs)

        CLIENTS[cache_key] = statsd_client

    return statsd_client


def get_metric(fn, tags):
    """
    Wraps the metric function to decorate with additional tags
    """
    @functools.wraps(fn)
    def wrapper(name, *args, **kwargs):
        # the metric name starts as the name of the function itself
        metric = fn.__func__.__name__

        _tags = tags.copy()
        _tags.update({
            'name': name,
        })

        tags_s = get_tags_string(_tags)
        full_name = f'{metric},{tags_s}'

        return fn(full_name, *args, **kwargs)

    return wrapper


def get_tags_string(tags):
    """
    Returns a comma-delimited k=v string

    Args:
        tags (dict): A dictionary of key/value pairs

    Returns:
        str
    """
    return ','.join([f'{k}={v}' for k, v in tags.items()])


def measure_function(client):
    """
    Decorator to measure a function

    This places a timer around the entire function and passes in a StatsdFactory instance as the function's `statsd` kwarg

    Args:
        client (StatsClient): statsd client instance
    """
    def decorator(fn):
        _statsd = client

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with _statsd.extra_tags({'def': fn.__name__}):
                _statsd.incr('calls')  # increment a counter for the function being called

                # inject statsd into the function call if the function has a statsd kwarg
                if 'statsd' in fn.__code__.co_varnames:
                    kwargs.update({
                        'statsd': _statsd,
                    })

                with _statsd.timer('duration'):
                    return fn(*args, **kwargs)

        return wrapper

    return decorator


class StatsClient(statsd.StatsClient):
    metrics_methods = [x for x in dir(StatsClientBase) if not x.startswith('_')]

    def __init__(self, **kwargs):
        self.tags = kwargs.pop('tags', {})

        super().__init__(**kwargs)

    def __getattribute__(self, attr):
        # when a non-metrics method is requested, pass through undecorated
        metrics_methods = super().__getattribute__('metrics_methods')
        if attr not in metrics_methods:
            return super().__getattribute__(attr)

        fn = super().__getattribute__(attr)

        # wrap the desired metric function
        return get_metric(fn, self.tags)

    @contextlib.contextmanager
    def extra_tags(self, tags):
        """
        Temporarily adds the given tags
        """
        obj = self
        tags_orig = obj.tags.copy()

        try:
            obj.tags.update(tags)

            yield
        finally:
            obj.tags = tags_orig

    def measure_function(self):
        """
        Returns a decorator to measure the function being decorated
        """
        return measure_function(self)
