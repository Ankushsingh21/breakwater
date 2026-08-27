"""Firestore wrapper. Only actually imports the SDK when USE_LOCAL_STORE=false."""
import os

_db = None


def _get_db():
    global _db
    if _db is None:
        from google.cloud import firestore
        _db = firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
    return _db


def write_record(entry):
    db = _get_db()
    collection = os.getenv("FIRESTORE_COLLECTION", "audit_trail")
    db.collection(collection).add(entry)


def read_all():
    db = _get_db()
    collection = os.getenv("FIRESTORE_COLLECTION", "audit_trail")
    return [doc.to_dict() for doc in db.collection(collection).stream()]
