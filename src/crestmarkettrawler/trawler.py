from gevent import monkey
from crestmarkettrawler.location import LocationService
monkey.patch_all()  # nopep8

from contrib import getAllItems, RateLimited
from emdr import EMDRUploader
from os import getenv
from postgres import PostgresAdapter
from Queue import PriorityQueue
from stats import StatsCollector, StatsWriter, StatsDBWriter
from _version import USER_AGENT_STRING, __version__ as VERSION

import logging
import os
import pycrest
import random
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


def getCachedMarketCall(eve, regionID):
    keys = [k for k in eve.cache._dict.keys() if 'market' in k[0] and str(regionID) in k[0]]
    if len(keys) >= 1:
        return eve.cache._dict[keys[0]]
    else:
        return {'expires': 0}


def getCacheExpiry(cachedCall):
    return cachedCall['expires']


class Trawler(object):
    def __init__(self, statsCollector):
        self._listeners = []
        self._regionsQueue = PriorityQueue()
        self.eve = pycrest.EVE(user_agent=USER_AGENT_STRING)
        self.eve._endpoint = "https://crest-tq.eveonline.com/"

        self.statsCollector = statsCollector
        statsCollector.datapoint("trawler_version", VERSION)
        self._locationService = LocationService()

    def addListener(self, listener):
        self._listeners.append(listener)

    def _notifyListeners(self, regionID, orders):
        for listener in self._listeners:
            listener.notify(regionID, orders)

    def _populateRegionsQueue(self):
        logger.info("Populating regions queue")
        regions = getRegions(self.eve)
        for region in regions:
            self._regionsQueue.put((random.randint(0, len(regions)), region))

    @RateLimited(REQUESTS_PER_SECOND)
    def limitPollRate(self):
        # This method's sole purpose is to sleep long enough that the CREST
        # rate limit is not exceeded - this is handled by the decorator.
        pass

    def trawlMarket(self):
        self._populateRegionsQueue()

        def processRegion(region):
            logger.info("Trawling for region {0}".format(region.name))
            cacheTime = 0  # if we fail, try again straight away
            try:
                orders = getAllItems(region.marketOrdersAll())
                processOrders(region, orders)
                cacheTime = getCacheExpiry(getCachedMarketCall(self.eve, region.id))

                cleanEveCache(self.eve)
                self.limitPollRate()

            except Exception as e:
                self.statsCollector.tally("trawler_exceptions")
                logger.exception(e)
            self._regionsQueue.put((cacheTime, region))
            self.statsCollector.tally("trawler_region_processed")

        def processOrders(region, orders):
            logger.info(u"Retrieved {0} orders for region {1} ({2})".format(len(orders), region.id, region.name))
            self.statsCollector.tally("trawler_orders_received", len(orders))
            logger.debug("Annotating orders with solarSystemID")
            for order in orders:
                if not hasattr(order, "solarSystemID") and order.stationID:
                    order.solarSystemID = self._locationService.solarSystemID(order.stationID)
            self._notifyListeners(region.id, orders)

        while True:
            (cacheTime, region) = self._regionsQueue.get()
            if cacheTime > time.time():
                logger.info("Region {} cached until {}, now {} - pausing".format(region.name, cacheTime, time.time()))
            while cacheTime > time.time():
                time.sleep(cacheTime - time.time())
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
    if not getenv("DISABLE_EMDR", False):
        u = EMDRUploader(s)
        t.addListener(u)
        u.start()
    if "POSTGRES_USERNAME" in os.environ:
        p = PostgresAdapter(s)
        t.addListener(p)
        p.start()
        sdw = StatsDBWriter(s)
        sdw.start()

    t.trawlMarket()


if __name__ == '__main__':
    main()
