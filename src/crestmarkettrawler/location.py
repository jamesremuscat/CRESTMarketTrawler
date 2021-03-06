import base64
import bz2file
import csv
import logging
import requests
import os
import urllib2
import xmltodict

from datetime import datetime, timedelta

from _version import USER_AGENT_STRING
from threading import Lock

logger = logging.getLogger("location")

_STA_STATIONS_URL = "https://www.fuzzwork.co.uk/dump/latest/staStations.csv.bz2"
_ESI_STRUCTURES_URL = "https://esi.tech.ccp.is/v1/universe/structures/{structure_id}"
_CONQUERABLE_STATIONS_URL = "https://api.eveonline.com/eve/ConquerableStationList.xml.aspx"
_STATION_ID_MIN = 60000000


class LocationService(object):

    def __init__(self):
        self._mapping = {}
        self._blacklist = []
        logger.info("Priming LocationService cache from Fuzzwork Enterprises...")

        fuzz = urllib2.Request(
            _STA_STATIONS_URL,
            headers={
                'User-Agent': USER_AGENT_STRING
            }
        )

        mapDenormalize = urllib2.urlopen(fuzz)
        bf = bz2file.BZ2File(mapDenormalize)
        md = csv.DictReader(bf)
        for row in md:
            itemID = int(row['stationID'])
            if itemID >= _STATION_ID_MIN:
                self._mapping[itemID] = row
        mapDenormalize.close()
        logger.info("{} locations cached".format(len(self._mapping)))

        logger.info("Incorporating conquerable stations list...")
        conq = urllib2.Request(
            _CONQUERABLE_STATIONS_URL,
            headers={
                'User-Agent': USER_AGENT_STRING
            }
        )
        csl = urllib2.urlopen(conq)

        conquerable_stations = xmltodict.parse(csl.read())

        for station in conquerable_stations["eveapi"]["result"]["rowset"]["row"]:
            self._mapping[int(station["@stationID"])] = {
                "solarSystemID": int(station["@solarSystemID"])
            }

        csl.close()
        logger.info("Now {} locations cached".format(len(self._mapping)))

        if "ESI_CLIENT_ID" in os.environ:
            logger.debug("Creating ESI TokenStore")
            self._token_store = TokenStore(
                os.environ.get("ESI_CLIENT_ID", None),
                os.environ.get("ESI_SECRET", None),
                os.environ.get("ESI_REFRESH_TOKEN", None)
            )
        else:
            self._token_store = None

        self._lock = Lock()

    def get(self, itemID):
        with self._lock:
            if itemID not in self._mapping and self._token_store and itemID not in self._blacklist:
                esi = requests.get(
                    _ESI_STRUCTURES_URL.format(structure_id=itemID),
                    headers={
                        'Authorization': "Bearer {}".format(self._token_store.getToken()),
                        'User-Agent': USER_AGENT_STRING
                    }
                )
                logger.debug("ESI returned status code {}".format(esi.status_code))
                if esi.status_code == requests.codes.ok:
                    logger.info("Retrieved data for structure {} via ESI".format(itemID))
                    data = esi.json()
                    self._mapping[itemID] = {'solarSystemID': data['solar_system_id']}
                    self._mapping[itemID].update(data)
                else:
                    # If we get an error trying to retrieve structure location,
                    # make a note of it and don't try again.
                    # This means we'll occasionally miss the location of structures
                    # that have become more public, but speeds things up on
                    # subsequent runs as we won't keep trying repeatedly.
                    self._blacklist.append(itemID)
                    return None

            return self._mapping.get(itemID)

    def solarSystemID(self, itemID):
        maybe = self.get(itemID)
        if maybe:
            return int(maybe['solarSystemID'])
        return None


class TokenStore(object):
    def __init__(self, client_id, secret, refresh_token):
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.secret = secret
        self.expiry = datetime.fromtimestamp(0)
        self.authToken = None

    def getToken(self):
        if self.expiry < datetime.now():
            self._refresh()
        return self.authToken

    def _refresh(self):
        rt = requests.post(
            "https://login.eveonline.com/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            },
            headers={
                'Authorization': "Basic {}".format(self._getBearer(self.client_id, self.secret)),
                'User-Agent': USER_AGENT_STRING
            }
        )
        rt.raise_for_status()
        if rt.status_code == requests.codes.ok:
            data = rt.json()
            self.authToken = data['access_token']
            self.expiry = datetime.now() + timedelta(seconds=data['expires_in'])

    def _getBearer(self, clientID, secret):
        return base64.b64encode(
            "{}:{}".format(
                clientID,
                secret
            )
        )
