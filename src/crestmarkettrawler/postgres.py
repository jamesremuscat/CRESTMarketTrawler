# This should already have been done in trawler but just in case!
import gevent
from gevent import monkey
gevent.monkey.patch_all()  # nopep8

from psycopg2._psycopg import IntegrityError
from Queue import Queue
from threading import Thread
import datetime
import dateutil.parser
import logging
import os
import psycopg2
import psycogreen.gevent
import re
psycogreen.gevent.patch_psycopg()

logger = logging.getLogger("postgres")


def rangeAdapter(rangeStr):
    if rangeStr == "station":
        return -1
    if rangeStr == "solarsystem":
        return 0
    if rangeStr == "region":
        return 32767
    return int(rangeStr)


class PostgresAdapter(Thread):
    def __init__(self, statsCollector):
        Thread.__init__(self)
        self._queue = Queue(maxsize=10)
        self.setDaemon(True)

        self.statsCollector = statsCollector

    def notify(self, regionID, orders):
        self._queue.put((regionID, orders))
        self.statsCollector.tally("database_queued")
        queueSize = self._queue.qsize()
        self.statsCollector.datapoint("postgres_queue_size", queueSize)
        if queueSize > 1000:
            logger.error("DB processing queue is about {0} items long!".format(queueSize))
        elif queueSize > 100:
            logger.warn("DB processing queue is about {0} items long!".format(queueSize))

    def run(self):
        conn = psycopg2.connect(user = os.environ.get("POSTGRES_USERNAME"), password = os.environ.get("POSTGRES_PASSWORD"), database = os.environ.get("POSTGRES_DB"), host = os.environ.get("POSTGRES_HOST", "localhost"))

        duplicateOrderID = re.compile('Key \(orderid\)=\(([0-9]+)\) already exists')

        while True:
            (regionID, orders) = self._queue.get()

            cursor = conn.cursor()

            logger.info("Processing {} orders for region {}".format(len(orders), regionID))

            cursor.execute("PREPARE insert_order (bigint, bigint, bigint, numeric, integer, smallint, integer, integer, boolean, timestamp without time zone, smallint, bigint, bigint, timestamp without time zone) AS INSERT INTO live_orders(orderID, typeID, regionID, price, volRemaining, range, volEntered, minVolume, isBid, issueDate, duration, stationID, solarSystemID, expiry) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)")


            cursor.execute("DELETE FROM live_orders WHERE regionID=%s", [regionID])

            for order in orders:
                realIssueDate = dateutil.parser.parse(order.issued)
                expiry = realIssueDate + datetime.timedelta(days = order.duration)
                try:
                    cursor.execute(
                        "EXECUTE insert_order (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (
                            order.id,
                            order.type,
                            regionID,
                            order.price,
                            order.volume,
                            rangeAdapter(order.range),
                            order.volumeEntered,
                            order.minVolume,
                            order.buy,
                            order.issued,
                            order.duration,
                            order.stationID,
                            None,
                            expiry
                        )
                    )
                    self.statsCollector.tally("database_submitted")
                    self.statsCollector.datapoint("database_last_updated", datetime.datetime.now().isoformat())
                except IntegrityError as e:
                    logger.error(e.message)
                    m = duplicateOrderID.match(e.message)
                    if m:
                        conn.rollback()
                        cursor.execute("DELETE FROM live_orders WHERE orderID=%s", [order.id])
                        self._queue.put(regionID, orders)  # If at first you don't succeed...

            logger.info("Finished processing region {}".format(regionID))

            cursor.execute("DEALLOCATE insert_order")
            conn.commit()
            cursor.close()
