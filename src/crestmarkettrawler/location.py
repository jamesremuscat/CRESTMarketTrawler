import bz2file
import csv
import logging
import requests
import os
import urllib2

from _version import USER_AGENT_STRING

logger = logging.getLogger("location")


class LocationService(object):
    _MAP_DENORMALIZE_URL = "https://www.fuzzwork.co.uk/dump/latest/mapDenormalize.csv.bz2"
    _ESI_STRUCTURES_URL = "https://esi.tech.ccp.is/v1/universe/structures/{structure_id}"
    _STATION_ID_MIN = 60000000
    _ESI_TOKEN = os.environ.get("ESI_TOKEN", None)

    def __init__(self):
        self._mapping = {}
        logging.info("Priming LocationService cache from Fuzzwork Enterprises...")

        fuzz = urllib2.Request(
            self._MAP_DENORMALIZE_URL,
            headers={
                'User-Agent': USER_AGENT_STRING
            }
        )

        mapDenormalize = urllib2.urlopen(fuzz)
        bf = bz2file.BZ2File(mapDenormalize)
        md = csv.DictReader(bf)
        for row in md:
            itemID = int(row['itemID'])
            if itemID >= self._STATION_ID_MIN:
                self._mapping[itemID] = row
        logging.info("{} locations cached".format(len(self._mapping)))

    def get(self, itemID):
        if itemID not in self._mapping:
            esi = requests.get(
                self._ESI_STRUCTURES_URL.format(structure_id=itemID),
                headers={
                    'Authorization': "Bearer {}".format(self._ESI_TOKEN),
                    'User-Agent': USER_AGENT_STRING
                }
            )
            if esi.status_code == requests.codes.ok:
                logging.info("Retrieved data for structure {} via ESI".format(itemID))
                data = esi.json()
                self._mapping[itemID] = {'solarSystemID': data['solar_system_id']}
                self._mapping[itemID].update(data)
            else:
                return None

        return self._mapping[itemID]

    def solarSystemID(self, itemID):
        maybe = self.get(itemID)
        if maybe:
            return int(maybe['solarSystemID'])
        return None
