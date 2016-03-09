from contrib import RateLimited
from random import choice
from requests import Session
import logging
import pycrest


def getByAttrVal(objlist, attr, val):
    ''' Searches list of dicts for a dict with dict[attr] == val '''
    matches = [getattr(obj, attr) == val for obj in objlist]
    index = matches.index(True)  # find first match, raise ValueError if not found
    return objlist[index]


def getAllItems(page):
    ''' Fetch data from all pages '''
    ret = page().items
    while hasattr(page(), 'next'):
        page = page().next()
        ret.extend(page().items)
    return ret


THERA_REGION = 11000031
WORMHOLE_REGIONS_START = 11000000


def trawlMarket():
    Session.get = RateLimited(20)(Session.get)
    eve = pycrest.EVE(cache_dir='cache/')
    items = [34, 35, 36]
    regions = [region() for region in eve().regions().items if region.id < WORMHOLE_REGIONS_START or region.id == THERA_REGION]
    while True:
        region = choice(regions)
        logging.info("Trawling region {0}".format(region.name))
        for item in items:
            sellOrders = region.marketSellOrders(type="https://public-crest.eveonline.com/types/{0}/".format(item)).items
            buyOrders = region.marketBuyOrders(type="https://public-crest.eveonline.com/types/{0}/".format(item)).items
            logging.info("Retrieved {0} orders for type {1}".format(len(sellOrders) + len(buyOrders), item))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    trawlMarket()
