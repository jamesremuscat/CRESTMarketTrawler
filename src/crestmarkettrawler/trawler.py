import gevent
from gevent import monkey
gevent.monkey.patch_all()  # nopep8

from contrib import getAllItems, RateLimited
from emdr import EMDRUploader
from os import getenv
from postgres import PostgresAdapter
from Queue import PriorityQueue
from stats import StatsCollector, StatsWriter
from _version import __version__ as VERSION

import logging
import pycrest
import time


THERA_REGION = 11000031
WORMHOLE_REGIONS_START = 11000000
REQUESTS_PER_SECOND = float(getenv("REQUESTS_PER_SECOND", "60"))


logger = logging.getLogger("trawler")


def getRegions(eve):
    return [region() for region in getAllItems(eve().regions()) if region.id < WORMHOLE_REGIONS_START or region.id == THERA_REGION]


def cleanEveCache(eve):
    """
    Reduce memory overhead by clearing out market orders from this eve.
    """
    keys = [k for k in eve.cache._dict.keys() if 'market' in k[0]]
    for key in keys:
        eve.cache._dict.pop(key)


class Trawler(object):
    def __init__(self, statsCollector):
        self._listeners = []
        self._regionsQueue = PriorityQueue()
        self.eve = pycrest.EVE(user_agent="CRESTMarketTrawler/{0} (muscaat@eve-markets.net)".format(VERSION))
        self.eve._endpoint = "https://crest-tq.eveonline.com/"

        self.statsCollector = statsCollector

    def addListener(self, listener):
        self._listeners.append(listener)

    def _notifyListeners(self, regionID, orders):
        for listener in self._listeners:
            listener.notify(regionID, orders)

    def _populateRegionsQueue(self):
        logger.info("Populating regions queue")
        for region in getRegions(self.eve):
            self._regionsQueue.put((0, region))

    @RateLimited(REQUESTS_PER_SECOND)
    def limitPollRate(self):
        # This method's sole purpose is to sleep long enough that the CREST
        # rate limit is not exceeded - this is handled by the decorator.
        pass

    def trawlMarket(self):
        self._populateRegionsQueue()

        def processRegion(region):
            logger.info("Trawling for region {0}".format(region.name))
            try:
                ordersPage = region.marketOrdersAll()
                processOrderPage(region, ordersPage.items)

                while hasattr(ordersPage(), 'next'):
                    self.limitPollRate()
                    ordersPage = ordersPage().next()
                    processOrderPage(region, ordersPage.items)

                cleanEveCache(self.eve)
                self.limitPollRate()

            except Exception as e:
                self.statsCollector.tally("trawler_exceptions")
                logger.exception(e)
            self.statsCollector.tally("trawler_region_processed")
            self._regionsQueue.put((time.time(), region))

        def processOrderPage(region, orders):
            logger.info(u"Retrieved {0} orders for region {1} ({2})".format(len(orders), region.id, region.name))
            self.statsCollector.tally("trawler_orders_received", len(orders))
            self._notifyListeners(region.id, orders)

        while True:
            (_, region) = self._regionsQueue.get()
            processRegion(region)


def main():
    logging.basicConfig(level=logging.INFO)
    # Hide messages caused by eve-emdr.com not supporting keep-alive
    logging.getLogger("requests").setLevel(logging.WARN)
    s = StatsCollector()
    sw = StatsWriter(s)
    s.start()
    sw.start()
    t = Trawler(s)
    u = EMDRUploader(s)
    t.addListener(u)
    u.start()
    p = PostgresAdapter(s)
    t.addListener(p)
    p.start()
    t.trawlMarket()


if __name__ == '__main__':
    main()
