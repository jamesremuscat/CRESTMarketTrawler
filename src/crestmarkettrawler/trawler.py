from contrib import RateLimited
from random import choice
from requests import Session
from _version import __version__ as VERSION
import logging
import pycrest


THERA_REGION = 11000031
WORMHOLE_REGIONS_START = 11000000
REQUESTS_PER_SECOND = 50


class Trawler(object):
    def __init__(self):
        Session.get = RateLimited(REQUESTS_PER_SECOND)(Session.get)
        self._eve = pycrest.EVE(cache_dir='cache/', user_agent="CRESTMarketTrawler/{0} (muscaat@eve-markets.net)".format(VERSION))

    def trawlMarket(self):
        items = [34, 35, 36]
        regions = [region() for region in self._eve().regions().items if region.id < WORMHOLE_REGIONS_START or region.id == THERA_REGION]
        while True:
            region = choice(regions)
            logging.info("Trawling region {0}".format(region.name))
            for item in items:
                sellOrders = region.marketSellOrders(type="https://public-crest.eveonline.com/types/{0}/".format(item)).items
                buyOrders = region.marketBuyOrders(type="https://public-crest.eveonline.com/types/{0}/".format(item)).items
                orders = sellOrders + buyOrders
                logging.info("Retrieved {0} orders for type {1}".format(len(orders), item))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    Trawler().trawlMarket()
