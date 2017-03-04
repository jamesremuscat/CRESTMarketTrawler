# First, apply geven monkey patches
from gevent import monkey
monkey.patch_all()  # nopep8

# Monkey patch requests with ujson for faster parsing
import requests
import ujson

requests.models.json = ujson
