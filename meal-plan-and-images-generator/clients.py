import config
from google.cloud import ndb
from mealhow_sdk.clients import CloudStorage, HttpClient

ndb_client = ndb.Client(database=config.DATASTORE_DB)
cloud_storage_session = CloudStorage()
http_client = HttpClient()
