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
    # ("solarSystemID", lambda _: -1)  # Not available through CREST :(
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


class EMDRUploader(object):
    def notify(self, regionID, orders):
        print "Received orders!"
        for order in orders:
            print EMDROrderAdapter(order)
