from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from aiohttp_openmetrics import metrics_middleware, request_counter


class MetricsMiddlewareTests(AioHTTPTestCase):
    async def get_application(self):
        async def handler_default(request):
            return web.Response(text="ok")

        async def handler_overridden(request):
            return web.Response(text="ok")

        handler_overridden._metric_name = "grouped"

        async def handler_also_overridden(request):
            return web.Response(text="ok")

        handler_also_overridden._metric_name = "grouped"

        app = web.Application(middlewares=[metrics_middleware])
        app.router.add_get("/default", handler_default, name="default_route")
        app.router.add_get("/a", handler_overridden, name="route_a")
        app.router.add_get("/b", handler_also_overridden, name="route_b")
        return app

    async def test_route_name_used_by_default(self):
        before = request_counter.labels("GET", "default_route", "200")._value.get()

        resp = await self.client.get("/default")
        self.assertEqual(200, resp.status)

        after = request_counter.labels("GET", "default_route", "200")._value.get()
        self.assertEqual(before + 1, after)

    async def test_metric_name_attribute_overrides_route_name(self):
        before = request_counter.labels("GET", "grouped", "200")._value.get()
        before_a = request_counter.labels("GET", "route_a", "200")._value.get()
        before_b = request_counter.labels("GET", "route_b", "200")._value.get()

        resp = await self.client.get("/a")
        self.assertEqual(200, resp.status)
        resp = await self.client.get("/b")
        self.assertEqual(200, resp.status)

        self.assertEqual(
            before + 2,
            request_counter.labels("GET", "grouped", "200")._value.get(),
        )
        self.assertEqual(
            before_a,
            request_counter.labels("GET", "route_a", "200")._value.get(),
        )
        self.assertEqual(
            before_b,
            request_counter.labels("GET", "route_b", "200")._value.get(),
        )
