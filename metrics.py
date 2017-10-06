# -*- coding: utf-8 -*-
"""
metrics helpers
"""
import functools
import statsd

from django.conf import settings

# clients indexed by prefix
CLIENTS = {}


class StatsClient(statsd.StatsClient):
    def measure_function(self):
        return measure_function(self)


def get_client(prefix=None):
    statsd_client = CLIENTS.get(prefix)
    if statsd_client is None:
        statsd_client = StatsClient('172.17.0.1', settings.STATSD_PORT, prefix=prefix)

        CLIENTS[prefix] = statsd_client

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
