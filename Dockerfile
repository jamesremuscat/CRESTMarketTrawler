FROM python:2.7

WORKDIR app
COPY . /app

RUN pip install --upgrade pip
RUN python setup.py install

ENTRYPOINT CRESTMarketTrawler
