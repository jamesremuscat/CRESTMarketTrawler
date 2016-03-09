from time import clock, sleep


# http://stackoverflow.com/a/667706/11643
def RateLimited(maxPerSecond):
    minInterval = 1.0 / float(maxPerSecond)

    def decorate(func):
        lastTimeCalled = [0.0]

        def rateLimitedFunction(*args, **kargs):
            elapsed = clock() - lastTimeCalled[0]
            leftToWait = minInterval - elapsed
            if leftToWait > 0:
                sleep(leftToWait)
            ret = func(*args, **kargs)
            lastTimeCalled[0] = clock()
            return ret
        return rateLimitedFunction
    return decorate
