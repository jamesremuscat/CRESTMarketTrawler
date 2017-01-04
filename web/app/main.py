from datetime import datetime
from flask import Flask, json

import os
import psycopg2

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False


def with_cursor(func):
    def inner(*args, **kwargs):
        with psycopg2.connect(
            user=os.environ.get("POSTGRES_USERNAME"),
            password=os.environ.get("POSTGRES_PASSWORD"),
            database=os.environ.get("POSTGRES_DB"),
            host=os.environ.get("POSTGRES_HOST", "localhost")
        ) as conn:
            with conn.cursor() as cur:
                return func(cur, *args, **kwargs)
    # Flask relies on the __name__ attribute of route()-decorated functions - so let's preserve it
    inner.__name__ = func.__name__
    return inner


@app.route("/prices")
@with_cursor
def prices(cur):
    cur.execute("SELECT typeid, buy_price, buy_volume, buy_min, buy_max, buy_sd, sell_price, sell_volume, sell_min, sell_max, sell_sd, median_price, time FROM live_prices")
    return json.jsonify(cur.fetchall())


@app.route("/region/<int:regionID>")
@with_cursor
def regional_prices(cur, regionID):
    cur.execute(
        "SELECT typeid, buy_price, buy_volume, buy_min, buy_max, buy_sd, sell_price, sell_volume, sell_min, sell_max, sell_sd, median_price, time FROM regional_prices WHERE regionid=%s",
        (regionID,)
    )
    return json.jsonify(cur.fetchall())

@app.route("/regions")
@with_cursor
def all_regional_prices(cur):
    cur.execute(
        "SELECT regionid, typeid, buy_price, buy_volume, buy_min, buy_max, buy_sd, sell_price, sell_volume, sell_min, sell_max, sell_sd, median_price, time FROM regional_prices"
    )
    return json.jsonify(cur.fetchall())

@app.route("/clean")
@with_cursor
def clean(cur):
    cur.execute("DELETE FROM live_orders WHERE expiry < NOW()")
    return json.jsonify({"deleted": cur.rowcount})


@app.route("/stats")
@with_cursor
def stats(cur):
    cur.execute("SELECT stats FROM trawler_stats ORDER BY time DESC LIMIT 1")
    statss = cur.fetchone()
    return json.jsonify(statss[0] if statss else {})

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)
