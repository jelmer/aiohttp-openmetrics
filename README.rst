aiohttp-openmetrics
===================

This project contains a simple middleware and /metrics route endpoint for
aiohttp that allow easy implementation of the
`openmetrics <https://www.openmetrics.org/>`_ protocol.

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

License
-------

This package is licensed under the Apache v2 or later license.
