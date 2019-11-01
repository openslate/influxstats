# -*- coding: utf-8 -*-
"""
metrics helpers
"""
import contextlib
import datetime
import functools
import hashlib
import inspect
import json

import statsd

try:
    from statsd.client import StatsClientBase
except ImportError:
    from statsd.client.base import StatsClientBase

from .logging import get_logger

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
    sha.update(json.dumps([args, kwargs]).encode("utf8"))

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
        tags = kwargs.pop("tags", {})
        tags.update({"module": module, "service": service})

        statsd_client = StatsClient(tags=tags, **kwargs)

        CLIENTS[cache_key] = statsd_client

    return statsd_client


def get_methods_classname(fn):
    """
    Returns a class-qualified function name
    """
    if inspect.isfunction(fn):
        return fn.__qualname__.split(".<locals>.", 1)[-1].rsplit(".", 1)[0]


def get_metric(fn, tags):
    """
    Wraps the metric function to decorate with additional tags
    """

    @functools.wraps(fn)
    def wrapper(name, *args, **kwargs):
        # the metric name starts as the name of the function itself
        metric = fn.__func__.__name__

        _tags = tags.copy()
        _tags.update({"name": name})

        tags_s = get_tags_string(_tags)
        full_name = f"{metric},{tags_s}"

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
    return ",".join([f"{k}={v}" for k, v in tags.items()])


def measure_function(client: "StatsClient", extra_tags: dict = None, log: bool = False):
    """
    Decorator to measure a function

    This places a timer around the entire function and passes in a StatsdFactory instance as the function's `statsd` kwarg

    Args:
        client (StatsClient): statsd client instance
        extra_tags (dict): optional extra tags to add to metrics
        log: whether to make logger calls, default False.  when logging, the logs are fired relative to the caller's scope
    """

    def decorator(fn):
        _statsd = client
        _extra_tags = extra_tags or {}

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            extra_tags = {"def": fn.__name__}

            # add any additional tags passed into measure_function()
            extra_tags.update(_extra_tags)

            fn_clsname = get_methods_classname(fn)
            if fn_clsname and fn_clsname != extra_tags["def"]:
                extra_tags.update({"class": fn_clsname})

            logger = None
            if log:
                logger = get_logger(rewind_stack=2)

            with _statsd.extra_tags(extra_tags):
                _statsd.incr(
                    "calls"
                )  # increment a counter for the function being called

                # inject statsd into the function call if the function has a statsd kwarg
                if "statsd" in fn.__code__.co_varnames:
                    kwargs.update({"statsd": _statsd})

                t0 = None
                if logger:
                    t0 = datetime.datetime.utcnow()

                    logger.info(
                        f"measure_function begin, t0={t0}, fn={fn}, args={args}, kwargs={kwargs}"
                    )

                try:
                    with _statsd.timer("duration"):
                        return fn(*args, **kwargs)
                finally:
                    if logger:
                        t1 = datetime.datetime.utcnow()
                        delta = t1 - t0

                        logger.info(
                            (
                                f"measure_function end, t0={t0}, fn={fn}, args={args}, kwargs={kwargs},"
                                " t1={t1}, delta={delta.total_seconds()}"
                            )
                        )

        return wrapper

    return decorator


class StatsClient(statsd.StatsClient):
    metrics_methods = [x for x in dir(StatsClientBase) if not x.startswith("_")]

    def __init__(self, **kwargs):
        self.tags = kwargs.pop("tags", {})

        super().__init__(**kwargs)

    def __getattribute__(self, attr):
        # when a non-metrics method is requested, pass through undecorated
        metrics_methods = super().__getattribute__("metrics_methods")
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

    def measure_function(self, extra_tags=None):
        """
        Returns a decorator to measure the function being decorated
        """
        return measure_function(self, extra_tags=extra_tags)

    def with_extra_tags(self, tags):
        """
        Returns a new StatsClient instance with existing tags and the new ones given
        """
        all_tags = self.tags.copy()
        all_tags.update(tags)

        return self.__class__(tags=all_tags)
