__version__ = (0, 0, 5)

__all__ = [
    'metrics_middleware',
    'metrics',
    'setup_metrics',
    'Counter',
    'Gauge',
    'Histogram',
    'REGISTRY',
    'run_prometheus_server',
    ]

import asyncio
import base64
import time
from typing import Optional, Dict
from urllib.parse import quote_plus

from aiohttp import web
from aiohttp.client import ClientSession, ClientTimeout
from yarl import URL

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

request_counter = Counter(
    "requests_total", "Total Request Count", ["method", "route", "status"]
)

request_latency_hist = Histogram(
    "request_latency_seconds", "Request latency", ["route"]
)

requests_in_progress_gauge = Gauge(
    "requests_in_progress_total", "Requests currently in progress",
    ["method", "route"]
)

request_exceptions = Counter(
    "request_exceptions_total", "Total Number of Exceptions during Requests",
    ["method", "route"])


async def metrics(request: web.Request) -> web.Response:
    resp = web.Response(body=generate_latest())
    resp.content_type = CONTENT_TYPE_LATEST
    return resp


@web.middleware
async def metrics_middleware(request: web.Request, handler) -> web.Response:
    start_time = time.time()
    route = request.match_info.route.name
    requests_in_progress_gauge.labels(request.method, route).inc()
    try:
        response = await handler(request)
    except (asyncio.CancelledError, web.HTTPException, ConnectionResetError):
        raise
    except Exception:
        request_exceptions.labels(request.method, route).inc()
        raise
    finally:
        resp_time = time.time() - start_time
        request_latency_hist.labels(route).observe(resp_time)
        requests_in_progress_gauge.labels(request.method, route).dec()
    request_counter.labels(request.method, route, response.status).inc()
    return response


def setup_metrics(app: web.Application):
    """Setup middleware and install metrics on app.
    """
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
    elif '/' in v:
        # Added in Pushgateway 0.9.0.
        return (
            k + "@base64",
            base64.urlsafe_b64encode(v.encode("utf-8")).decode("utf-8"))
    else:
        return k, quote_plus(v)


async def push_to_gateway(
        gateway: str, job: str, registry, timeout: int = 30,
        grouping_key: Optional[Dict[str, str]] = None):
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

    for (k, v) in sorted((grouping_key or {}).items()):
        (k, v) = _escape_grouping_key(k, v)
        url = url / k / v

    data = generate_latest(registry)

    async with ClientSession() as session:
        async with session.put(
                url, timeout=ClientTimeout(timeout),
                content_type=CONTENT_TYPE_LATEST, data=data,
                raise_for_status=True):
            pass
