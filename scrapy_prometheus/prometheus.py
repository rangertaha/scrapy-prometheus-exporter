import logging

from prometheus_client.twisted import MetricsResource
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor
from scrapy import signals

logger = logging.getLogger(__name__)


class Prometheus(Site):
    """

    """
    def __init__(self, crawler):
        self.crawler = crawler
        self.port = crawler.settings.get('PROMETHEUS_PORT', 8888)
        self.host = crawler.settings.get('PROMETHEUS_HOST', '127.0.0.1')
        self.path = crawler.settings.get('PROMETHEUS_PATH', 'metrics')

        self.root = Resource()
        self.root.putChild(self.path, MetricsResource())
        self.noisy = False

        crawler.signals.connect(self.start_listening, signals.engine_started)
        crawler.signals.connect(self.stop_listening, signals.engine_stopped)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def start_listening(self):
        print self.crawler.stats.get_stats()
        factory = Site(self.root)
        reactor.listenTCP(self.port, factory)
        reactor.run()

        logger.debug('Exporting metrics on port 8888')

    def stop_listening(self):
        reactor.stop()
