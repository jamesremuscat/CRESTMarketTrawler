# This should already have been done in trawler but just in case!
from gevent import monkey
monkey.patch_all()  # nopep8

from _version import __version__ as VERSION, USER_AGENT_STRING
from contrib import timestampString
from gevent.pool import Pool
from Queue import Queue
from tempfile import TemporaryFile
from threading import Thread
from requests.sessions import Session

import gzip
import logging
import os
import ujson

logger = logging.getLogger("emdr")

COLUMNS = [
    ("price", lambda o: o.price),
    ("volRemaining", lambda o: o.volume),
    ("range", lambda o: rangeAdapter(o.range)),
    ("orderID", lambda o: o.id),
    ("volEntered", lambda o: o.volumeEntered),
    ("minVolume", lambda o: o.minVolume),
    ("bid", lambda o: o.buy),
    ("issueDate", lambda o: o.issued + "+00:00"),
    ("duration", lambda o: o.duration),
    ("stationID", lambda o: o.stationID),
    ("solarSystemID", lambda o: o.solarSystemID)
]

COL_NAMES = [col[0] for col in COLUMNS]
COL_FUNCTIONS = [col[1] for col in COLUMNS]

CHUNK_SIZE = 30000

# Without a limit on the queue size, we'll eat up memory storing multiple copies
# of all market orders in New Eden, since we can poll CREST faster than we can
# POST to EMDR! Likewise there's no point setting this to larger than the number
# of regions in the first place (70 or so).
EMDR_QUEUE_SIZE = int(os.getenv("EMDR_QUEUE_SIZE", "20"))


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


def EMDROrdersAdapter(generationTime, regionID, orders):
    rowsets = []
    idIndex = COL_NAMES.index("orderID")
    for (typeID, typeOrders) in splitOrdersPerType(orders).iteritems():
        rows = [EMDROrderAdapter(order) for order in typeOrders]
        # Sort by orderID to facilitate caching by consumers
        rows.sort(key=lambda order: order[id_index])
        rowsets.append({
            "generatedAt": generationTime,
            "regionID": regionID,
            "typeID": typeID,
            "rows": rows
        })
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
        "rowsets": rowsets
    }


def splitOrdersPerType(orders):
    perType = {}
    for order in orders:
        if order.type not in perType:
            perType[order.type] = []
        perType[order.type].append(order)
    return perType


def chunkOrders(orders):
    chunks = []
    perType = splitOrdersPerType(orders)
    currentChunk = []
    while perType:
        typeid, typeOrders = perType.popitem()
        if len(currentChunk) + len(typeOrders) > CHUNK_SIZE:
            chunks.append(currentChunk)
            currentChunk = []
        logger.debug("Adding {} orders for type {} to chunk #{}".format(len(typeOrders), typeid, len(chunks)))
        currentChunk += typeOrders
    chunks.append(currentChunk)
    return chunks


class EMDRUploader(Thread):
    def __init__(self, statsCollector):
        Thread.__init__(self)
        self._queue = Queue(EMDR_QUEUE_SIZE)
        self.setDaemon(True)
        self._session = Session()
        self._session.headers.update({
            "User-Agent": USER_AGENT_STRING
        })
        self._pool = Pool(size=10)
        self.statsCollector = statsCollector

    def notify(self, regionID, orders):
        self._queue.put((timestampString(), regionID, orders))
        self.statsCollector.tally("emdr_send_queued")
        queueSize = self._queue.qsize()
        self.statsCollector.datapoint("emdr_queue_size", queueSize)
        if queueSize > EMDR_QUEUE_SIZE / 2:
            logger.warn("EMDR submit queue is about {0} items long!".format(queueSize))

    def run(self):
        def submit(generationTime, regionID, orders):
            chunks = chunkOrders(orders)
            for idx, orderChunk in enumerate(chunks):
                with TemporaryFile() as gzfile:
                    ujson.dump(
                        EMDROrdersAdapter(generationTime, regionID, orderChunk),
                        gzip.GzipFile(fileobj=gzfile, mode="wb")
                    )
                    headers = {'Content-Length': str(gzfile.tell()),
                               'Content-Encoding': 'gzip',  # what EMDR wants
                               # 'Transfer-Encoding': 'gzip'  # what is strictly true
                               }
                    gzfile.seek(0, 0)
                    logger.info(
                        "Submitting to EMDR for region {} (chunk {} of {})".format(regionID, idx + 1, len(chunks)))
                    res = self._session.post("http://upload.eve-emdr.com/upload/", data=gzfile, headers=headers)
                    self.statsCollector.tally("emdr_chunks_sent")
                if res.status_code != 200:
                    logger.error("Error {0} submitting to EMDR: {1}".format(res.status_code, res.content))
                    self.statsCollector.tally("emdr_errored")

        while True:
            (generationTime, regionID, orders) = self._queue.get()
            self.statsCollector.datapoint("emdr_queue_size", self._queue.qsize())
            self._pool.spawn(submit, generationTime, regionID, orders)
