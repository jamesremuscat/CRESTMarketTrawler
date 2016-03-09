from contrib import getAllItems, RateLimited
from emdr import EMDRUploader
from random import choice
from requests import Session
from _version import __version__ as VERSION
import logging
import pycrest


THERA_REGION = 11000031
WORMHOLE_REGIONS_START = 11000000
REQUESTS_PER_SECOND = 50


logger = logging.getLogger("trawler")


class Trawler(object):
    def __init__(self):
        Session.get = RateLimited(REQUESTS_PER_SECOND)(Session.get)
        self._eve = pycrest.EVE(cache_dir='cache/', user_agent="CRESTMarketTrawler/{0} (muscaat@eve-markets.net)".format(VERSION))
        self._listeners = []

    def addListener(self, listener):
        self._listeners.append(listener)

    def _notifyListeners(self, regionID, typeID, orders):
        for listener in self._listeners:
            listener.notify(regionID, typeID, orders)

    def getItemList(self):
        # This is basically a cheat around having to enumerate all types in
        # market groups, or worse, having to poll for each item to find its
        # market group ID!
        return [item.type for item in getAllItems(self._eve().marketPrices())]

    def trawlMarket(self):
        items = self.getItemList()
        regions = [region() for region in self._eve().regions().items if region.id < WORMHOLE_REGIONS_START or region.id == THERA_REGION]
        while True:
            region = choice(regions)
            logger.info("Trawling region {0}".format(region.name))
            for item in items:
                sellOrders = region.marketSellOrders(type=item.href).items
                buyOrders = region.marketBuyOrders(type=item.href).items
                orders = sellOrders + buyOrders
                logger.info(u"Retrieved {0} orders for {1}".format(len(orders), item.name))
                self._notifyListeners(region.id, item.id, orders)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    t = Trawler()
    u = EMDRUploader()
    t.addListener(u)
    u.start()
    t.trawlMarket()
