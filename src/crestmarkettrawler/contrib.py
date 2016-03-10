from datetime import datetime
from time import time, sleep


def timestampString():
    now = datetime.utcnow().replace(microsecond=0)
    return now.isoformat() + "+00:00"  # Be explicit because some clients are lax!


# http://stackoverflow.com/a/667706/11643
def RateLimited(maxPerSecond):
    minInterval = 1.0 / float(maxPerSecond)

    def decorate(func):
        lastTimeCalled = [0.0]

        def rateLimitedFunction(*args, **kargs):
            elapsed = time() - lastTimeCalled[0]
            leftToWait = minInterval - elapsed
            if leftToWait > 0:
                sleep(leftToWait)
            ret = func(*args, **kargs)
            lastTimeCalled[0] = time()
            return ret
        return rateLimitedFunction
    return decorate


# http://pycrest.readthedocs.org/en/latest/
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
