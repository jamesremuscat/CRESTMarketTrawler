from _version import __version__ as VERSION
from contrib import timestampString
from Queue import Queue
from threading import Thread

COLUMNS = [
    ("price", lambda o: o.price),
    ("volRemaining", lambda o: o.volume),
    ("range", lambda o: rangeAdapter(o.range)),
    ("orderID", lambda o: o.id),
    ("volEntered", lambda o: o.volumeEntered),
    ("minVolume", lambda o: o.minVolume),
    ("bid", lambda o: o.buy),
    ("issueDate", lambda o: o.issued),
    ("duration", lambda o: o.duration),
    ("stationID", lambda o: o.location.id),
    ("solarSystemID", lambda _: None)  # Not available through CREST :(
]


COL_NAMES = [col[0] for col in COLUMNS]
COL_FUNCTIONS = [col[1] for col in COLUMNS]


def rangeAdapter(rangeStr):
    if rangeStr == "station":
        return -1
    if rangeStr == "solarsystem":
        return 0
    if rangeStr == "region":
        return 32767
    return int(rangeStr)


def EMDROrderAdapter(order):
    return [adapt(order) for adapt in COL_FUNCTIONS]


def EMDROrdersAdapter(generationTime, regionID, typeID, orders):
    rows = [EMDROrderAdapter(order) for order in orders]
    return {
        "resultType": "orders",
        "version": "0.1",
        "uploadKeys": [],
        "generator": {
            "name": "CRESTMarketTrawler",
            "version": VERSION
        },
        "currentTime": timestampString(),
        "columns": COL_NAMES,
        "rowsets": [
            {
                "generatedAt": generationTime,
                "regionID": regionID,
                "typeID": typeID,
                "rows": rows
            }
        ]
    }


class EMDRUploader(Thread):
    def __init__(self):
        Thread.__init__(self)
        self._queue = Queue()
        self.setDaemon(True)

    def notify(self, regionID, typeID, orders):
        self._queue.put((timestampString(), regionID, typeID, orders))

    def run(self):
        while True:
            (generationTime, regionID, typeID, orders) = self._queue.get()
            print EMDROrdersAdapter(generationTime, regionID, typeID, orders)
