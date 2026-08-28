aiohttp-openmetrics
===================

This project contains a simple middleware and /metrics route endpoint for
aiohttp that allow easy implementation of the
`openmetrics <https://www.openmetrics.io/>`_ protocol.

At the moment, this package is a thin wrapper around the ``prometheus_client``
package.

Example usage
-------------

.. code-block:: python

  from aiohttp import web
  from aiohttp_openmetrics import metrics, metrics_middleware

  app = web.Application()
  app.middlewares.append(metrics_middlware)
  app.router.add_get('/metrics', metrics)

  web.run_app(app)

Configuring latency histogram buckets
-------------------------------------

The default latency histogram uses ``prometheus_client``'s default buckets,
which top out at 10 seconds. If your requests routinely take longer (or are
much faster) you can pass custom bucket boundaries to ``setup_metrics``:

.. code-block:: python

  from aiohttp import web
  from aiohttp_openmetrics import setup_metrics

  app = web.Application()
  setup_metrics(app, latency_buckets=[1, 5, 10, 30, 60, 120, 300, 600])

License
-------

This package is licensed under the Apache v2 or later license.
