# CRESTMarketTrawler
EVE Online market data trawler and EMDR uploader.

## Installation

We recommend using `virtualenv` to help manage Python dependencies.

Then from your Git checkout:

```bash
virtualenv venv
source venv/bin/activate
python setup.py install
```

Dependencies will be installed to the virtualenv environment automatically.
You may need the `libpq-dev` or `libpq-devel` package installed in order for
Python to build some of the dependencies.

## Running

Simple case:
```bash
venv/bin/CRESTMarketTrawler
```

Or from within the virtualenv environment, just run `CRESTMarketTrawler`.

## Throttling

The trawler will automatically ensure that the CREST API's cache timers are obeyed.

You can further restrict the trawl speed by setting the `REQUESTS_PER_SECOND` environment
variable. This will limit the maximum number of requests to CREST per second; setting it
to smaller fractional values will introduce larger pauses between requests.

## Location service

CREST (and ESI) do not include `solarSystemID` in the data feed, but many EMDR
clients rely on its presence. CRESTMarketTrawler includes a location service
that uses the Static Data Export to provide orders with `solarSystemID`s. If
the `ESI_CLIENT_ID`, `ESI_SECRET` and `ESI_REFRESH_TOKEN` environment variables
are set, it will also call ESI to obtain `solarSystemID`s for player structures
(e.g. citadels).

To obtain a client ID and secret, register an application at
https://developers.eveonline.com. Authenticate a character granting the
`esi-universe.read_structures.v1` scope to obtain a refresh token.

## Postgres

To enable writing orders to a Postgres database, you should set the `POSTGRES_USERNAME`,
`POSTGRES_PASSWORD`, `POSTGRES_HOST` and `POSTGRES_DB` environment variables. At the
moment, the destination must be a table called `live_orders` and conform to the following
schema:

```sql
CREATE TABLE live_orders (
    orderid bigint NOT NULL,
    typeid bigint,
    regionid bigint,
    price numeric,
    volremaining integer,
    range smallint,
    volentered integer,
    minvolume integer,
    isbid boolean,
    issuedate timestamp without time zone,
    duration smallint,
    stationid bigint,
    solarsystemid bigint,
    expiry timestamp without time zone
);
```

## Disabling EMDR upload

To disable uploading to EMDR, set the `DISABLE_EMDR` environment variable to `1`.
