import config
from aiohttp import ClientSession as Session
from gcloud.aio.storage import Storage
from google.cloud import ndb
from http_client import HttpClient


class CloudStorage:
    storage: Storage = None

    def initialise(self, session: Session) -> None:
        self.storage = Storage(session=session)

    def __call__(self) -> Storage:
        assert self.storage is not None
        return self.storage


ndb_client = ndb.Client(database=config.DATASTORE_DB)
cloud_storage_session = CloudStorage()
http_client = HttpClient()
