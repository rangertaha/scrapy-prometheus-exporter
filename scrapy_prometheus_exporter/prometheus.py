import logging

from prometheus_client.twisted import MetricsResource
from prometheus_client import Counter, Summary
from twisted.web.server import Site
from twisted.web import server, resource
from twisted.internet import task
from scrapy.exceptions import NotConfigured
from scrapy.utils.reactor import listen_tcp
from scrapy import signals

logger = logging.getLogger(__name__)


class WebService(Site):
    """

    """
    def __init__(self, crawler):
        if not crawler.settings.getbool('PROMETHEUS_ENABLED', True):
            raise NotConfigured
        self.tasks = []
        self.stats = crawler.stats
        self.crawler = crawler
        self.name = crawler.settings.get('BOT_NAME')
        self.port = crawler.settings.get('PROMETHEUS_PORT', [9410])
        self.host = crawler.settings.get('PROMETHEUS_HOST', '0.0.0.0')
        self.path = crawler.settings.get('PROMETHEUS_PATH', 'metrics')
        self.interval = crawler.settings.get('PROMETHEUS_UPDATE_INTERVAL', 30)

        self.spr_item_scraped = Counter(
            'spr_items_scraped', 'Spider items scraped', ['spider'])
        self.spr_item_dropped = Counter(
            'spr_items_dropped', 'Spider items dropped', ['spider'])
        self.spr_response_received = Counter(
            'spr_response_received', 'Spider responses received', ['spider'])
        self.spr_opened = Counter('spr_opened', 'Spider opened', ['spider'])
        self.spr_closed = Counter(
            'spr_closed', 'Spider closed', ['spider', 'reason'])

        self.spr_downloader_request_bytes = Summary(
            'spr_downloader_request_bytes', '...', ['spider'])
        self.spr_downloader_request_total = Summary(
            'spr_downloader_request_total', '...', ['spider'])
        self.spr_downloader_request_count = Summary(
            'spr_downloader_request', '...', ['spider', 'method'])
        self.spr_downloader_response_count = Summary(
            'spr_downloader_response', '...', ['spider'])
        self.spr_downloader_response_bytes = Summary(
            'spr_downloader_response_bytes', '...', ['spider'])
        self.spr_downloader_response_status_count = Summary(
            'spr_downloader_response_status', '...', ['spider', 'code'])

        self.spr_log_count = Summary('spr_log', '...', ['spider', 'level'])

        self.spr_duplicate_filtered = Summary(
            'spr_duplicate_filtered', '...', ['spider'])

        self.spr_memdebug_gc_garbage_count = Summary(
            'spr_memdebug_gc_garbage', '...', ['spider'])
        self.spr_memdebug_live_refs = Summary(
            'spr_memdebug_live_refs', '...', ['spider'])
        self.spr_memusage_max = Summary(
            'spr_memusage_max', '...', ['spider'])
        self.spr_memusage_startup = Summary(
            'spr_memusage_startup', '...', ['spider'])

        self.spr_scheduler_dequeued = Summary(
            'spr_scheduler_dequeued', '...', ['spider'])
        self.spr_scheduler_enqueued = Summary(
            'spr_scheduler_enqueued', '...', ['spider'])
        self.spr_scheduler_enqueued_memory = Summary(
            'spr_scheduler_enqueued_memory', '...', ['spider'])

        self.spr_offsite_domains_count = Summary(
            'spr_offsite_domains', '...', ['spider'])
        self.spr_offsite_filtered_count = Summary(
            'spr_offsite_filtered', '...', ['spider'])

        root = resource.Resource()
        self.promtheus = None
        root.putChild(self.path, MetricsResource())
        server.Site.__init__(self, root)

        crawler.signals.connect(self.engine_started, signals.engine_started)
        crawler.signals.connect(self.engine_stopped, signals.engine_stopped)

        crawler.signals.connect(self.spider_opened, signals.spider_opened)
        crawler.signals.connect(self.spider_closed, signals.spider_closed)
        crawler.signals.connect(self.item_scraped, signals.item_scraped)
        crawler.signals.connect(self.item_dropped, signals.item_dropped)
        crawler.signals.connect(self.response_received,
                                signals.response_received)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def engine_started(self):
        # Start server endpoint for exporting metrics
        self.promtheus = listen_tcp(self.port, self.host, self)

        # Periodically update the metrics
        tsk = task.LoopingCall(self.update)
        self.tasks.append(tsk)
        tsk.start(self.interval, now=True)

    def engine_stopped(self):
        # Stop all periodic tasks
        for tsk in self.tasks:
            if tsk.running:
                tsk.stop()

        # Stop metrics exporting
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
        logging.debug(self.stats.get_stats())

        # Downloader Request Stats
        self.request_stats()

        # Downloader Request Stats
        self.response_stats()

        # Logging Stats
        self.logging_stats()

        # Memory Debug Stats
        self.memory_debug_stats()

        # Memory Usage Stats
        self.memory_usage_stats()

        # Scheduler Stats
        self.scheduler_stats()

        # Off-Site Filtering Stats
        self.offsite_stats()

        # Duplicate Stats
        self.duplicate_filter_stats()

        # Request Depth
        self.request_depth()

    def request_depth(self):
        depth = self.stats.get_value('request_depth_max', 0)
        for i in range(depth):
            stat = 'request_depth_count/{}'.format(i)
            self.stats.get_value(stat, 0)

    def duplicate_filter_stats(self):
        dup = self.stats.get_value('dupefilter/filtered', 0)
        self.spr_duplicate_filtered.labels(spider=self.name).observe(dup)

    def memory_debug_stats(self):
        mdgc_count = self.stats.get_value('memdebug/gc_garbage_count', 0)
        self.spr_memdebug_gc_garbage_count.labels(
            spider=self.name).observe(mdgc_count)

        mdlr_count = self.stats.get_value('memdebug/live_refs/MySpider', 0)
        self.spr_memdebug_live_refs.labels(
            spider=self.name).observe(mdlr_count)

    def memory_usage_stats(self):
        mum_count = self.stats.get_value('memusage/max', 0)
        self.spr_memusage_max.labels(spider=self.name).observe(mum_count)

        mus_count = self.stats.get_value('memusage/startup', 0)
        self.spr_memusage_startup.labels(spider=self.name).observe(mus_count)

    def scheduler_stats(self):
        dequeued = self.stats.get_value('scheduler/dequeued', 0)
        self.spr_scheduler_dequeued.labels(spider=self.name).observe(dequeued)

        enqueued = self.stats.get_value('scheduler/enqueued', 0)
        self.spr_scheduler_enqueued.labels(spider=self.name).observe(enqueued)

        enqueued_mem = self.stats.get_value('scheduler/enqueued/memory', 0)
        self.spr_scheduler_enqueued_memory.labels(
            spider=self.name).observe(enqueued_mem)

        dequeued_mem = self.stats.get_value('scheduler/dequeued/memory', 0)
        self.spr_scheduler_enqueued_memory.labels(
            spider=self.name).observe(dequeued_mem)

    def offsite_stats(self):
        od_count = self.stats.get_value('offsite/domains', 0)
        self.spr_offsite_domains_count.labels(
            spider=self.name).observe(od_count)

        of_count = self.stats.get_value('offsite/filtered', 0)
        self.spr_offsite_filtered_count.labels(
            spider=self.name).observe(of_count)

        print dir(self.stats.get_stats())

    def request_stats(self):
        for i in ['GET', 'PUT', 'DELETE', 'POST']:
            stat = 'downloader/request_method_count/{}'.format(i)
            count = self.stats.get_value(stat, 0)
            self.spr_downloader_request_count.labels(
                spider=self.name, method=i).observe(count)

        total_count = self.stats.get_value('downloader/request_count', 0)
        self.spr_downloader_request_total.labels(
            spider=self.name).observe(total_count)

        request_bytes = self.stats.get_value('downloader/request_bytes', 0)
        self.spr_downloader_request_bytes.labels(
            spider=self.name).observe(request_bytes)

    def response_stats(self):
        response_count = self.stats.get_value('downloader/response_count', 0)
        self.spr_downloader_response_count.labels(
            spider=self.name).observe(response_count)

        for i in ['200', '404', '500']:
            stat = 'downloader/response_status_count/{}'.format(i)
            status = self.stats.get_value(stat, 0)
            self.spr_downloader_response_status_count.labels(
                spider=self.name, code=i).observe(status)

        response_bytes = self.stats.get_value('downloader/response_bytes', 0)
        self.spr_downloader_response_bytes.labels(
            spider=self.name).observe(response_bytes)

    def logging_stats(self):
        for i in ['DEBUG', 'ERROR', 'INFO', 'CRITICAL', 'WARNING']:
            level = self.stats.get_value('log_count/{}'.format(i), 0)
            self.spr_log_count.labels(
                spider=self.name, level=i).observe(level)
