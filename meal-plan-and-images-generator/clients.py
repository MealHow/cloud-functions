from google.cloud import storage, datastore

import config
from http_client import HttpClient

datastore_client = datastore.Client(database=config.DATASTORE_DB)
storage_client = storage.Client()
http_client = HttpClient()
