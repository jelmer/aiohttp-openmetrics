__version__ = (0, 0, 12)

__all__ = [
    "REGISTRY",
    "Counter",
    "Gauge",
    "Histogram",
    "metrics",
    "metrics_middleware",
    "run_prometheus_server",
    "setup_metrics",
]

import asyncio
import base64
import time
from collections.abc import Sequence
from urllib.parse import quote_plus

from aiohttp import web
from aiohttp.client import ClientSession, ClientTimeout
from prometheus_client.exposition import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)
from prometheus_client.metrics import (
    Counter,
    Gauge,
    Histogram,
)
from prometheus_client.registry import (
    REGISTRY,
)
from yarl import URL

request_counter = Counter(
    "requests_total", "Total Request Count", ["method", "route", "status"]
)

request_connection_reset_counter = Counter(
    "requests_connection_reset_total",
    "Total Number of Requests where the connection was reset",
    ["method", "route"],
)

request_cancelled_counter = Counter(
    "requests_cancelled_total",
    "Total Number of Requests that were cancelled",
    ["method", "route"],
)

request_latency_hist = Histogram(
    "request_latency_seconds", "Request latency", ["route"]
)

requests_in_progress_gauge = Gauge(
    "requests_in_progress_total", "Requests currently in progress", ["method", "route"]
)

request_exceptions = Counter(
    "request_exceptions_total",
    "Total Number of Exceptions during Requests",
    ["method", "route"],
)


async def metrics(request: web.Request) -> web.Response:
    resp = web.Response(body=generate_latest(registry=REGISTRY))
    resp.content_type = CONTENT_TYPE_LATEST
    return resp


@web.middleware
async def metrics_middleware(request: web.Request, handler) -> web.Response:
    start_time = time.monotonic()
    route = request.match_info.route.name
    requests_in_progress_gauge.labels(request.method, route).inc()
    try:
        response = await handler(request)
    except web.HTTPException as e:
        request_counter.labels(request.method, route, e.status_code).inc()
        raise
    except ConnectionResetError:
        request_connection_reset_counter.labels(request.method, route).inc()
        raise
    except asyncio.CancelledError:
        request_cancelled_counter.labels(request.method, route).inc()
        raise
    except Exception:
        request_exceptions.labels(request.method, route).inc()
        raise
    finally:
        resp_time = time.monotonic() - start_time
        request_latency_hist.labels(route).observe(resp_time)
        requests_in_progress_gauge.labels(request.method, route).dec()
    request_counter.labels(request.method, route, response.status).inc()
    return response


def setup_metrics(
    app: web.Application,
    latency_buckets: Sequence[float] | None = None,
):
    """Setup middleware and install metrics on app.

    Args:
      app: aiohttp application to install the middleware on
      latency_buckets: Optional custom bucket boundaries for the request
        latency histogram, in seconds. If provided, replaces the default
        histogram buckets (see prometheus_client.Histogram for the default).
        A trailing ``+Inf`` bucket is added automatically by
        prometheus_client if not present.
    """
    if latency_buckets is not None:
        global request_latency_hist
        REGISTRY.unregister(request_latency_hist)
        request_latency_hist = Histogram(
            "request_latency_seconds",
            "Request latency",
            ["route"],
            buckets=tuple(latency_buckets),
        )
    app.middlewares.insert(0, metrics_middleware)
    app.router.add_get("/metrics", metrics, name="metrics")


async def run_prometheus_server(listen_addr: str, port: int):
    """Convenience function to run a web server with metrics only.

    Args:
      listen_addr: Address to listen on
      port: Port to listen on
    """
    app = web.Application()
    setup_metrics(app)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, listen_addr, port)
    await site.start()


# _escape_grouping_key imported from pprometheus-client @
# https://github.com/prometheus/client_python
def _escape_grouping_key(k, v):
    if v == "":
        # Per https://github.com/prometheus/pushgateway/pull/346.
        return k + "@base64", "="
    elif "/" in v:
        # Added in Pushgateway 0.9.0.
        return (
            k + "@base64",
            base64.urlsafe_b64encode(v.encode("utf-8")).decode("utf-8"),
        )
    else:
        return k, quote_plus(v)


async def push_to_gateway(
    gateway: str,
    job: str,
    registry,
    timeout: int = 30,
    grouping_key: dict[str, str] | None = None,
):
    """Push results to a pushgateway.

    Args:
      gateway: URL to the push gateway
      job: Name of the exported job
      registry: Registry to get variables from
      timeout: Timeout in seconds
      grouping_key: Dict with key/values to add
    """
    (k, v) = _escape_grouping_key("job", job)
    url = URL(gateway) / "metrics" / k / v

    for k, v in sorted((grouping_key or {}).items()):
        (k, v) = _escape_grouping_key(k, v)
        url = url / k / v

    data = generate_latest(registry)

    async with (
        ClientSession() as session,
        session.put(
            url,
            timeout=ClientTimeout(timeout),
            headers={"Content-Type": CONTENT_TYPE_LATEST},
            data=data,
            raise_for_status=True,
        ),
    ):
        pass
