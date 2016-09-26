FROM tiangolo/uwsgi-nginx-flask:flask

RUN pip install psycopg2 simplejson

EXPOSE 80

COPY ./app /app
