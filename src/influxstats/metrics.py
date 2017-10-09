# -*- coding: utf-8 -*-
"""
metrics helpers
"""
import functools
import hashlib
import json

import statsd

from django.conf import settings

# clients indexed by prefix
CLIENTS = {}


class StatsClient(statsd.StatsClient):
    def measure_function(self):
        """
        Returns a decorator to measure the function being decorated
        """
        return measure_function(self)


def get_cache_key(kwargs):
    """
    Returns a cache key from the given kwargs

    This is simply a sha256 hexdigest of the keyword arguments

    Args:
        kwargs (dict): the arguments to build a cache key from

    Returns:
        str: the cache key
    """
    sha = hashlib.sha256()
    sha.update(json.dumps(kwargs))

    return sha.hexdigest()


def get_client(**kwargs):
    """
    Returns a StatsClient instance

    Args:
        **kwargs: options passed directly to StatsClient

    Returns:
        StatsClient instance
    """
    cache_key = get_cache_key(kwargs)

    statsd_client = CLIENTS.get(cache_key)
    if statsd_client is None:
        statsd_client = StatsClient(**kwargs)

        CLIENTS[cache_key] = statsd_client

    return statsd_client


def measure_function(client):
    """
    Decorator to measure a function

    This places a timer around the entire function and passes in a StatsdFactory instance as the function's `statsd` kwarg

    Args:
        client (StatsdClient): statsd client instance
    """
    def decorator(fn):
        _statsd = StatsdWrapper(client, fn.__name__)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            _statsd.incr('calls')  # increment a counter for the function being called

            # inject statsd into the function call if defined as a function param
            if 'statsd' in fn.__code__.co_varnames:
                kwargs.update({
                    'statsd': _statsd,
                })

            with _statsd.timer('total'):
                return fn(*args, **kwargs)

        return wrapper

    return decorator


def get_metric(client, attr, extra):
    def wrapper(name, *args, **kwargs):
        full_name = '{},name={}'.format(attr, name)
        if extra:
            full_name = '{},{}'.format(full_name, extra)

        return getattr(client, attr)(full_name, *args, **kwargs)

    return wrapper


class StatsdWrapper(object):
    def __init__(self, client, function_name=None):
        self.client = client
        self.function_name = function_name

    def __getattribute__(self, attr):
        client = super(StatsdWrapper, self).__getattribute__('client')
        function_name = super(StatsdWrapper, self).__getattribute__('function_name')

        extra = ''
        if function_name:
            extra = 'def={}'.format(function_name)

        return get_metric(client, attr, extra)
