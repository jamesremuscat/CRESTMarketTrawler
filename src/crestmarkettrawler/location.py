import bz2file
import csv
import logging
import urllib2

logger = logging.getLogger("location")


class LocationService(object):
    _MAP_DENORMALIZE_URL = "https://www.fuzzwork.co.uk/dump/latest/mapDenormalize.csv.bz2"
    _STATION_ID_MIN = 60000000

    def __init__(self):
        self._mapping = {}
        logging.info("Priming LocationService cache from Fuzzwork Enterprises...")
        mapDenormalize = urllib2.urlopen(self._MAP_DENORMALIZE_URL)
        bf = bz2file.BZ2File(mapDenormalize)
        md = csv.DictReader(bf)
        for row in md:
            itemID = int(row['itemID'])
            if itemID >= self._STATION_ID_MIN:
                self._mapping[itemID] = row
        logging.info("{} locations cached".format(len(self._mapping)))

    def get(self, itemID):
        return self._mapping[itemID]

    def solarSystemID(self, itemID):
        if itemID in self._mapping:
            return int(self._mapping[itemID]['solarSystemID'])
        return None
