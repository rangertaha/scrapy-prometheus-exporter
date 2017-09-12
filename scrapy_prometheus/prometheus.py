import uuid
import logging
import datetime

from prometheus_client.twisted import MetricsResource
from prometheus_client import Counter, Summary, Gauge
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
        self.uuid = uuid.uuid4().hex
        self.name = crawler.settings.get('BOT_NAME')
        self.port = crawler.settings.get('PROMETHEUS_PORT', 8888)
        self.host = crawler.settings.get('PROMETHEUS_HOST', '127.0.0.1')
        self.path = crawler.settings.get('PROMETHEUS_PATH', 'metrics')

        self.spider_item_scraped = Counter('spider_items_scraped', 'Number of items scraped', ['name', 'uuid'])
        self.spider_item_dropped = Counter('spider_items_dropped', 'Number of items dropped', ['name', 'uuid'])
        self.spider_response_received = Counter('spider_response_received', 'Number of responses received', ['name', 'uuid'])
        self.spider_opened_count = Counter('spider_opened_count', 'Spider opened count', ['name', 'uuid'])
        self.spider_closed_count = Counter('spider_closed_count', 'Spider closed count', ['name', 'uuid'])

        # from prometheus_client import Gauge
        # g = Gauge('my_inprogress_requests', 'Description of gauge')
        # g.inc()  # Increment by 1
        # g.dec(10)  # Decrement by given value
        # g.set(4.2)  # Set to a given value
        #
        # from prometheus_client import Summary
        # s = Summary('request_latency_seconds', 'Description of summary')
        # s.observe(4.7)  # Observe 4.7 (seconds in this case)

        self.root = Resource()
        self.root.putChild(self.path, MetricsResource())
        self.noisy = False

        crawler.signals.connect(self.start_listening, signals.engine_started)
        crawler.signals.connect(self.stop_listening, signals.engine_stopped)

    @classmethod
    def from_crawler(cls, crawler):
        o = cls(crawler)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(o.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(o.item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(o.response_received, signal=signals.response_received)
        return o

    def start_listening(self):
        print self.crawler.stats.get_stats()
        factory = Site(self.root)
        reactor.listenTCP(self.port, factory)
        reactor.run()

        logger.debug('Exporting metrics on port 8888')

    def stop_listening(self):
        reactor.stop()

    def spider_opened(self, spider):
        self.spider_opened_count.labels(name=self.name, uuid=self.uuid).inc()

    def spider_closed(self, spider, reason):
        self.spider_closed_count.labels(name=self.name, uuid=self.uuid).inc()

    def item_scraped(self, item, spider):
        self.spider_item_scraped.labels(name=self.name, uuid=self.uuid).inc()

    def response_received(self, spider):
        self.spider_response_received.labels(name=self.name, uuid=self.uuid).inc()

    def item_dropped(self, item, spider, exception):
        self.spider_item_scraped.labels(name=self.name, uuid=self.uuid).inc()
