from contrib import getAllItems, RateLimited
from emdr import EMDRUploader
from Queue import PriorityQueue
from requests import Session
from _version import __version__ as VERSION

import logging
import pycrest
import time


THERA_REGION = 11000031
WORMHOLE_REGIONS_START = 11000000
REQUESTS_PER_SECOND = 50


logger = logging.getLogger("trawler")


def getEVE():
    return pycrest.EVE(cache_dir='cache/', user_agent="CRESTMarketTrawler/{0} (muscaat@eve-markets.net)".format(VERSION))


class Trawler(object):
    def __init__(self):
        Session.get = RateLimited(REQUESTS_PER_SECOND)(Session.get)
        self._eve = getEVE()
        self._listeners = []
        self._itemQueue = PriorityQueue()

    def addListener(self, listener):
        self._listeners.append(listener)

    def _notifyListeners(self, regionID, typeID, orders):
        for listener in self._listeners:
            listener.notify(regionID, typeID, orders)

    def populateItemQueue(self):
        # Use of marketPrices() is basically a cheat around having to enumerate
        # all types in market groups, or worse, having to poll for each item to
        # find its market group ID!
        for item in getAllItems(self._eve().marketPrices()):
            self._itemQueue.put((0, item.type))

    def trawlMarket(self):
        self.populateItemQueue()
        regions = [region() for region in self._eve().regions().items if region.id < WORMHOLE_REGIONS_START or region.id == THERA_REGION]
        while True:
            (_, item) = self._itemQueue.get()
            logger.info("Trawling for item {0}".format(item.name))
            for region in regions:
                sellOrders = region.marketSellOrders(type=item.href).items
                buyOrders = region.marketBuyOrders(type=item.href).items
                orders = sellOrders + buyOrders
                logger.info(u"Retrieved {0} orders for {1} in region {2}".format(len(orders), item.name, region.name))
                self._notifyListeners(region.id, item.id, orders)
            self._itemQueue.put((time.time(), item))


def main():
    logging.basicConfig(level=logging.INFO)
    t = Trawler()
    u = EMDRUploader()
    t.addListener(u)
    u.start()
    t.trawlMarket()


if __name__ == '__main__':
    main()
