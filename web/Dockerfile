FROM tiangolo/uwsgi-nginx-flask:flask

RUN pip install psycopg2 ujson

EXPOSE 80

COPY ./app /app

# Overwrite base image's default conf
COPY ./nginx.conf /etc/nginx/conf.d/
