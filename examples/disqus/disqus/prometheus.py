import sys
import time
import logging

from prometheus_client.twisted import MetricsResource
from prometheus_client import Counter, Summary, Gauge
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.web import server, resource
from twisted.internet import reactor, task
from scrapy.utils.reactor import listen_tcp
from scrapy import signals

logger = logging.getLogger(__name__)



class Prometheus(Site):
    """

    """
    def __init__(self, crawler):
        self.tasks = []
        self.stats = crawler.stats
        self.crawler = crawler
        #self.uuid = uuid.uuid4().hex
        self.name = crawler.settings.get('BOT_NAME')
        self.port = crawler.settings.get('PROMETHEUS_PORT', 8888)
        self.host = crawler.settings.get('PROMETHEUS_HOST', '127.0.0.1')
        self.path = crawler.settings.get('PROMETHEUS_PATH', 'metrics')
        self.interval = crawler.settings.get('PROMETHEUS_UPDATE_INTERVAL', 1)

        self.spr_item_scraped = Counter('spr_items_scraped', 'Spider items scraped', ['spider'])
        self.spr_item_dropped = Counter('spr_items_dropped', 'Spider items dropped', ['spider'])
        self.spr_response_received = Counter('spr_response_received', 'Spider responses received', ['spider'])
        self.spr_opened = Counter('spr_opened', 'Spider opened', ['spider'])
        self.spr_closed = Counter('spr_closed', 'Spider closed', ['spider', 'reason'])

        self.spr_downloader_request_bytes = Summary('spr_downloader_request_bytes', '...', ['spider'])
        self.spr_downloader_request_count = Summary('spr_downloader_request', '...', ['spider'])
        self.spr_downloader_request_get_count = Summary('spr_downloader_request_get', '...', ['spider'])
        self.spr_downloader_response_count = Summary('spr_downloader_response', '...', ['spider'])
        self.spr_downloader_response_status_count = Summary('spr_downloader_response_status', '...', ['spider', 'code'])

        self.spr_log_count = Summary('spr_log', '...', ['spider', 'level'])

        self.spr_memdebug_gc_garbage_count = Summary('spr_memdebug_gc_garbage', '...', ['spider'])
        self.spr_memdebug_live_refs = Summary('spr_memdebug_live_refs', '...', ['spider'])
        self.spr_memusage_max = Summary('spr_memusage_max', '...', ['spider'])
        self.spr_memusage_startup = Summary('spr_memusage_startup', '...', ['spider'])

        self.spr_scheduler_dequeued = Summary('spr_scheduler_dequeued', '...', ['spider'])
        self.spr_scheduler_enqueued = Summary('spr_scheduler_enqueued', '...', ['spider'])
        self.spr_scheduler_enqueued_memory = Summary('spr_scheduler_enqueued_memory', '...', ['spider'])

        self.spr_offsite_domains_count = Summary('spr_offsite_domains', '...', ['spider'])
        self.spr_offsite_filtered_count = Summary('spr_offsite_filtered', '...', ['spider'])


        # self.root = Resource()
        # self.root.putChild(self.path, MetricsResource())
        # self.noisy = True

        root = Resource()
        self.promtheus = None
        root.putChild(self.path, MetricsResource())
        server.Site.__init__(self, root)

        crawler.signals.connect(self.engine_started, signals.engine_started)
        crawler.signals.connect(self.engine_stopped, signals.engine_stopped)

        crawler.signals.connect(self.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(self.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(self.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(self.item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(self.response_received, signal=signals.response_received)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def engine_started(self):
        self.promtheus = listen_tcp([self.port], self.host, self)
        self.update()

        # Periodically update the metrics
        tsk = task.LoopingCall(self.update)
        self.tasks.append(tsk)
        tsk.start(self.interval, now=True)

    def engine_stopped(self):
        for tsk in self.tasks:
            if tsk.running:
                tsk.stop()

        # Stop Prometheus metrics server
        self.promtheus.stopListening()

    def spider_opened(self, spider):
        self.spr_opened.labels(spider=self.name).inc()

    def spider_closed(self, spider, reason):
        self.spr_closed.labels(spider=self.name, reason=reason).inc()

    def item_scraped(self, item, spider):
        self.spr_item_scraped.labels(spider=self.name).inc()

    def response_received(self, spider):
        self.spr_response_received.labels(spider=self.name).inc()

    def item_dropped(self, item, spider, exception):
        self.spr_item_scraped.labels(spider=self.name).inc()

    def update(self):

        bytes = self.stats.get_value('downloader/request_bytes', 0)
        self.spr_downloader_request_bytes.labels(spider=self.name).observe(bytes)


        count = self.stats.get_value('downloader/request_count', 0)
        self.spr_downloader_request_count.labels(spider=self.name).observe(count)


        count = self.stats.get_value('downloader/request_method_count/GET', 0)
        self.spr_downloader_request_get_count.labels(spider=self.name).observe(count)

        count = self.stats.get_value('downloader/response_count', 0)
        self.spr_downloader_response_count.labels(spider=self.name).observe(count)

        count = self.stats.get_value('downloader/response_status_count/200', 0)
        self.spr_downloader_response_status_count.labels(spider=self.name, code='200').observe(count)


        count = self.stats.get_value('log_count/DEBUG', 0)
        self.spr_log_count.labels(spider=self.name, level='DEBUG').observe(count)


        count = self.stats.get_value('log_count/ERROR', 0)
        self.spr_log_count.labels(spider=self.name, level='ERROR').observe(count)


        count = self.stats.get_value('log_count/INFO', 0)
        self.spr_log_count.labels(spider=self.name, level='INFO').observe(count)


        count = self.stats.get_value('memdebug/gc_garbage_count', 0)
        self.spr_memdebug_gc_garbage_count.labels(spider=self.name).observe(count)


        count = self.stats.get_value('memdebug/live_refs/MySpider', 0)
        self.spr_memdebug_live_refs.labels(spider=self.name).observe(count)


        count = self.stats.get_value('memusage/max', 0)
        self.spr_memusage_max.labels(spider=self.name).observe(count)


        count = self.stats.get_value('memusage/startup', 0)
        self.spr_memusage_startup.labels(spider=self.name).observe(count)


        count = self.stats.get_value('scheduler/dequeued', 0)
        self.spr_scheduler_dequeued.labels(spider=self.name).observe(count)


        count = self.stats.get_value('scheduler/enqueued', 0)
        self.spr_scheduler_enqueued.labels(spider=self.name).observe(count)


        count = self.stats.get_value('scheduler/enqueued/memory', 0)
        self.spr_scheduler_enqueued_memory.labels(spider=self.name).observe(count)


        count = self.stats.get_value('offsite/domains', 0)
        self.spr_offsite_domains_count.labels(spider=self.name).observe(count)


        count = self.stats.get_value('offsite/filtered', 0)
        self.spr_offsite_filtered_count.labels(spider=self.name).observe(count)
