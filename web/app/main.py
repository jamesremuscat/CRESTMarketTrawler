from datetime import datetime
from flask import Flask, json
from psycopg2.extras import RealDictCursor

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
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM live_prices")
        return json.jsonify(cur.fetchall())

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)
