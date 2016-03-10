import gevent
from gevent import monkey
gevent.monkey.patch_all()  # nopep8

from contrib import getAllItems, RateLimited
from emdr import EMDRUploader
from gevent.pool import Pool
from Queue import Queue, PriorityQueue
from _version import __version__ as VERSION

import logging
import pycrest
import time


THERA_REGION = 11000031
WORMHOLE_REGIONS_START = 11000000
REQUESTS_PER_SECOND = 60
SIMULTANEUOUS_WORKERS = 5


logger = logging.getLogger("trawler")


def getRegions(eve):
    return [region() for region in eve().regions().items if region.id < WORMHOLE_REGIONS_START or region.id == THERA_REGION]


class pooled_eve():
    def __init__(self, eves):
        self.eves = eves

    def __enter__(self):
        self.myEve = self.eves.get()
        return self.myEve

    def __exit__(self, *args):
        # Reduce memory overhead by clearing out market orders from this eve
        keys = [k for k in self.myEve.cache._cache.keys() if 'market' in k[0]]
        for key in keys:
            self.myEve.cache._cache.pop(key)
        self.eves.put(self.myEve)


class Trawler(object):
    def __init__(self):
        self._listeners = []
        self._itemQueue = PriorityQueue()
        self._pool = Pool(size=SIMULTANEUOUS_WORKERS)
        evePool = Queue(SIMULTANEUOUS_WORKERS)
        for _ in range(SIMULTANEUOUS_WORKERS):
            newEve = pycrest.EVE(cache_dir='cache/', user_agent="CRESTMarketTrawler/{0} (muscaat@eve-markets.net)".format(VERSION))
            evePool.put(newEve)
        self.pooledEVE = lambda: pooled_eve(evePool)

    def addListener(self, listener):
        self._listeners.append(listener)

    def _notifyListeners(self, regionID, typeID, orders):
        for listener in self._listeners:
            listener.notify(regionID, typeID, orders)

    def populateItemQueue(self):
        # Use of marketPrices() is basically a cheat around having to enumerate
        # all types in market groups, or worse, having to poll for each item to
        # find its market group ID!
        with self.pooledEVE() as eve:
            for item in getAllItems(eve().marketPrices()):
                self._itemQueue.put((0, item.type))

    @RateLimited(REQUESTS_PER_SECOND / 2.0)  # Each call to processItem() makes two CREST calls
    def limitPollRate(self):
        # This method is called by each of the greenlets polling the CREST API.
        # Its sole purpose is to sleep long enough that the CREST rate limit is
        # not exceeded - this is handled by the decorator.
        pass

    def trawlMarket(self):
        self.populateItemQueue()

        def processItem(item):
            logger.info("Trawling for item {0}".format(item.name))
            with self.pooledEVE() as eve:
                for region in getRegions(eve):
                    sellOrders = region.marketSellOrders(type=item.href).items
                    buyOrders = region.marketBuyOrders(type=item.href).items
                    orders = sellOrders + buyOrders
                    logger.info(u"Retrieved {0} orders for {1} in region {2}".format(len(orders), item.name, region.name))
                    self._notifyListeners(region.id, item.id, orders)
                    self.limitPollRate()
                self._itemQueue.put((time.time(), item))

        while True:
            (_, item) = self._itemQueue.get()
            self._pool.spawn(processItem, item)


def main():
    logging.basicConfig(level=logging.INFO)
    # Hide messages caused by eve-emdr.com not supporting keep-alive
    logging.getLogger("requests").setLevel(logging.WARN)
    t = Trawler()
    u = EMDRUploader()
    t.addListener(u)
    u.start()
    t.trawlMarket()


if __name__ == '__main__':
    main()
