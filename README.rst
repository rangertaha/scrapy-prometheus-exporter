==========================
scrapy-prometheus-exporter
==========================

scrapy-prometheus-exporter is an extension to export Scrapy stats to be used
with Prometheus

Grafana Dashboard
=================


.. image:: /grafana/grafana.png
   :height: 100px
   :width: 200 px
   :scale: 50 %
   :alt: Grafana dashboard of the exported data
   :align: center

Installation
============

Install scrapy-prometheus-exporter using ``pip``::

    $ pip install scrapy-prometheus-exporter

Configuration
=============

First, you need to include the extension to your ``EXTENSIONS`` dict in
``settings.py``, for example::

    EXTENSIONS = {
        'scrapy_prometheus_exporter.prometheus.WebService': 500,
    }

By default the extension is enabled. To disable the extension you need to
set `PROMETHEUS_ENABLED`_ to ``False``.

The web server will listen on a port specified in `PROMETHEUS_PORT`_
(by default, it will try to listen on port 9410)

The endpoint for accessing exported metrics is::

    http://0.0.0.0:9410/metrics



Settings
========

These are the settings that control the metrics exporter:

PROMETHEUS_ENABLED
------------------

Default: ``True``

A boolean which specifies if the exporter will be enabled (provided its
extension is also enabled).


PROMETHEUS_PORT
---------------

Default: ``[6080]``

The port to use for the web service. If set to ``None`` or ``0``, a
dynamically assigned port is used.

PROMETHEUS_HOST
---------------

Default: ``'0.0.0.0'``

The interface the web service should listen on.


PROMETHEUS_PATH
---------------

Default: ``'metrics'``

The url path to access exported metrics Example::

    http://0.0.0.0:9410/metrics


PROMETHEUS_UPDATE_INTERVAL
--------------------------

Default: ``30``

This extensions periodically collects stats for exporting. The interval in
seconds between metrics updates can be controlled with this setting.
