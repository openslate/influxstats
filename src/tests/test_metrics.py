import mock

from unittest import TestCase

from influxstats.metrics import StatsClient, get_client


@mock.patch("influxstats.metrics.StatsClient.incr", create=True)
@mock.patch("influxstats.metrics.StatsClient.timer", create=True)
class MetricsTestCase(TestCase):
    def _setup_incr(self, *mocks):
        incr_mock = mocks[-1]
        incr_mock.__func__ = mock.Mock(__name__="incr")

        return incr_mock

    def _setup_timer(self, *mocks):
        timer_mock = mocks[-2]
        timer_mock.__func__ = mock.Mock(__name__="timer")

        return timer_mock

    @property
    def client(self):
        return get_client("test", __name__)

    def test_get_client(self, *mocks):
        """
        Ensure the client is the wrapped StatsClient
        """
        client = self.client

        self.assertEqual(StatsClient, client.__class__)

    def test_measure_function_attr(self, *mocks):
        """
        ensure __getattribute__ returns measure_function
        """
        client = self.client

        fn = client.measure_function

        self.assertEqual(StatsClient.measure_function, fn.__func__)

    def test_emit(self, *mocks):
        incr_mock = self._setup_incr(*mocks)

        client = self.client

        client.incr("fool")

        statsd_mock = mocks[0]

        incr_mock.assert_called_with(
            "incr,module=tests.test_metrics,service=test,name=fool"
        )

    def test_emit_no_tags(self, *mocks):
        """
        A client with no extra tags
        """
        incr_mock = self._setup_incr(*mocks)

        client = StatsClient()

        client.incr("fool")

        statsd_mock = mocks[0]

        incr_mock.assert_called_with("incr,name=fool")

    def test_extra_tags(self, *mocks):
        incr_mock = self._setup_incr(*mocks)

        client = self.client

        with client.extra_tags({"def": "something"}):
            client.incr("shoes")

        incr_mock.assert_called_with(
            "incr,module=tests.test_metrics,service=test,def=something,name=shoes"
        )

    def test_measure_function(self, *mocks):
        incr_mock = self._setup_incr(*mocks)
        timer_mock = self._setup_timer(*mocks)

        client = self.client

        @client.measure_function()
        def wrapped_fn():
            pass

        wrapped_fn()

        incr_mock.assert_called_with(
            "incr,module=tests.test_metrics,service=test,def=wrapped_fn,name=calls"
        )
        timer_mock.assert_called_with(
            "timer,module=tests.test_metrics,service=test,def=wrapped_fn,name=duration"
        )

    def test_measure_function_class_method(self, *mocks):
        incr_mock = self._setup_incr(*mocks)
        timer_mock = self._setup_timer(*mocks)

        client = self.client

        class TestClass(object):
            @client.measure_function()
            def wrapped_fn(self):
                pass

        TestClass().wrapped_fn()

        incr_mock.assert_called_with(
            "incr,module=tests.test_metrics,service=test,def=wrapped_fn,class=TestClass,name=calls"
        )
        timer_mock.assert_called_with(
            "timer,module=tests.test_metrics,service=test,def=wrapped_fn,class=TestClass,name=duration"
        )

    def test_measure_function_extra_tags(self, *mocks):
        incr_mock = self._setup_incr(*mocks)
        timer_mock = self._setup_timer(*mocks)

        client = self.client

        @client.measure_function(extra_tags={"foo": "one"})
        def wrapped_fn():
            pass

        wrapped_fn()

        incr_mock.assert_called_with(
            "incr,module=tests.test_metrics,service=test,def=wrapped_fn,foo=one,name=calls"
        )

    def test_with_extra_tags(self, *mocks):
        incr_mock = self._setup_incr(*mocks)

        client = self.client

        # this call has the base client tags
        client.incr("client")

        incr_mock.assert_called_with(
            "incr,module=tests.test_metrics,service=test,name=client"
        )

        # create a new client instance with an additional tag
        client2 = client.with_extra_tags({"another": "true"})
        client2.incr("client2")

        incr_mock.assert_called_with(
            "incr,module=tests.test_metrics,service=test,another=true,name=client2"
        )

        # create a new client instance on top of the second client
        client3 = client2.with_extra_tags({"yet_another": "yay"})
        client3.incr("client3")

        incr_mock.assert_called_with(
            "incr,module=tests.test_metrics,service=test,another=true,yet_another=yay,name=client3"
        )

        # create a different instance on top of the base client
        client2b = client.with_extra_tags({"another": "true"})
        client2b.incr("client2b")

        incr_mock.assert_called_with(
            "incr,module=tests.test_metrics,service=test,another=true,name=client2b"
        )
