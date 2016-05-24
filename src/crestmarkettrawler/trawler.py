import gevent
from gevent import monkey
gevent.monkey.patch_all()  # nopep8

from contrib import getAllItems, RateLimited
from emdr import EMDRUploader
from gevent.pool import Pool
from os import getenv
from Queue import Queue, PriorityQueue
from stats import StatsCollector, StatsWriter
from _version import __version__ as VERSION

import logging
import pycrest
import time


THERA_REGION = 11000031
WORMHOLE_REGIONS_START = 11000000
REQUESTS_PER_SECOND = float(getenv("REQUESTS_PER_SECOND", "60"))
SIMULTANEUOUS_WORKERS = int(getenv("NUM_CONNECTIONS", "5"))


logger = logging.getLogger("trawler")


def getRegions(eve):
    return [region() for region in getAllItems(eve().regions()) if region.id < WORMHOLE_REGIONS_START or region.id == THERA_REGION]


class pooled_eve():
    def __init__(self, eves):
        self.eves = eves

    def __enter__(self):
        self.myEve = self.eves.get()
        return self.myEve

    def __exit__(self, *args):
        # Reduce memory overhead by clearing out market orders from this eve
        keys = [k for k in self.myEve.cache._dict.keys() if 'market' in k[0]]
        for key in keys:
            self.myEve.cache._dict.pop(key)
        self.eves.put(self.myEve)


class Trawler(object):
    def __init__(self, statsCollector):
        self._listeners = []
        self._regionsQueue = PriorityQueue()
        self._pool = Pool(size=SIMULTANEUOUS_WORKERS)
        evePool = Queue(SIMULTANEUOUS_WORKERS)
        for _ in range(SIMULTANEUOUS_WORKERS):
            newEve = pycrest.EVE(user_agent="CRESTMarketTrawler/{0} (muscaat@eve-markets.net)".format(VERSION))
            newEve._endpoint = "https://crest-tq.eveonline.com/"
            evePool.put(newEve)
        self.pooledEVE = lambda: pooled_eve(evePool)
        self.statsCollector = statsCollector

    def addListener(self, listener):
        self._listeners.append(listener)

    def _notifyListeners(self, regionID, orders):
        for listener in self._listeners:
            listener.notify(regionID, orders)

    def _populateRegionsQueue(self):
        logger.info("Populating regions queue")
        with self.pooledEVE() as eve:
            for region in getRegions(eve):
                self._regionsQueue.put((0, region))

    @RateLimited(REQUESTS_PER_SECOND / 2.0)  # Each call to processItem() makes two CREST calls
    def limitPollRate(self):
        # This method is called by each of the greenlets polling the CREST API.
        # Its sole purpose is to sleep long enough that the CREST rate limit is
        # not exceeded - this is handled by the decorator.
        pass

    def trawlMarket(self):
        self._populateRegionsQueue()

        def processRegion(region):
            logger.info("Trawling for region {0}".format(region.name))
            try:
                orders = getAllItems(region.marketOrdersAll)
                logger.info(u"Retrieved {0} orders for region {1}".format(len(orders), region.name))
                self.statsCollector.tally("trawler_orders_received", len(orders))

                self._notifyListeners(region.id,  orders)

                self.limitPollRate()

            except Exception as e:
                self.statsCollector.tally("trawler_exceptions")
                logger.exception(e)
            self.statsCollector.tally("trawler_item_processed")
            self._regionsQueue.put((time.time(), region))

        while True:
            (_, region) = self._regionsQueue.get()
            self._pool.spawn(processRegion, region)


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
    t.trawlMarket()


if __name__ == '__main__':
    main()
