# Monkey patch requets with ujson for faster parsing
import requests
import ujson

requests.models.json = ujson
