from datetime import datetime
from flask import Flask, json

import os
import psycopg2

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False


conn = psycopg2.connect(
    user=os.environ.get("POSTGRES_USERNAME"),
    password=os.environ.get("POSTGRES_PASSWORD"),
    database=os.environ.get("POSTGRES_DB"),
    host=os.environ.get("POSTGRES_HOST", "localhost")
)


@app.route("/prices")
def prices():
    with conn.cursor() as cur:
        cur.execute("SELECT typeid, buy_price, buy_volume, buy_min, buy_max, buy_sd, sell_price, sell_volume, sell_min, sell_max, sell_sd, median_price, time FROM live_prices")
        return json.jsonify(cur.fetchall())

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)
