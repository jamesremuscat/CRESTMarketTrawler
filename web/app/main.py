from datetime import datetime
from flask import Flask
from psycopg2.extras import RealDictCursor

import os
import psycopg2
import simplejson

app = Flask(__name__)


conn = psycopg2.connect(
    user=os.environ.get("POSTGRES_USERNAME"),
    password=os.environ.get("POSTGRES_PASSWORD"),
    database=os.environ.get("POSTGRES_DB"),
    host=os.environ.get("POSTGRES_HOST", "localhost")
)


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")


@app.route("/prices")
def prices():
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM live_prices")
        return simplejson.dumps(cur.fetchall(), default=json_serial)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)
