"""In-memory stand-in for google.cloud.firestore.Client, covering exactly the
subset of the API lmd.store.repository/audit use: collection/document,
set/get/update, and where/order_by/limit/stream on a query.

This exists because the real thing needs a live Firestore project or the
Firestore emulator (a separate Java process), and this machine has neither
Docker nor a JRE (CLAUDE.md section 2). The fake is deliberately built only
against the same public method calls repository.py/audit.py make, so a test
written against it exercises the real query shapes (filter, order, limit)
without needing network access -- it is not a general Firestore emulator.
"""
from __future__ import annotations

import uuid
from typing import Any


class FakeDocSnapshot:
    def __init__(self, doc_id: str, data: dict | None):
        self.id = doc_id
        self.exists = data is not None
        self._data = data

    def to_dict(self) -> dict | None:
        return dict(self._data) if self._data is not None else None


class FakeDocRef:
    def __init__(self, collection: "FakeCollectionStore", doc_id: str):
        self._collection = collection
        self.id = doc_id

    def set(self, data: dict) -> None:
        self._collection.docs[self.id] = dict(data)

    def update(self, data: dict) -> None:
        existing = self._collection.docs.setdefault(self.id, {})
        existing.update(data)

    def get(self) -> FakeDocSnapshot:
        return FakeDocSnapshot(self.id, self._collection.docs.get(self.id))


class FakeCollectionStore:
    """Backing dict for one collection, shared by every FakeQuery/FakeDocRef
    derived from the same FakeFirestoreClient.collection(name) call."""

    def __init__(self):
        self.docs: dict[str, dict] = {}


def _matches(value: Any, op: str, target: Any) -> bool:
    if op == "==":
        return value == target
    raise NotImplementedError(f"fake firestore does not implement operator {op!r}")


class FakeQuery:
    def __init__(self, store: FakeCollectionStore, filters=None, order=None, limit_n=None):
        self._store = store
        self._filters = filters or []
        self._order = order
        self._limit_n = limit_n

    def where(self, field: str, op: str, value: Any) -> "FakeQuery":
        return FakeQuery(self._store, self._filters + [(field, op, value)], self._order, self._limit_n)

    def order_by(self, field: str, direction: str = "ASCENDING") -> "FakeQuery":
        return FakeQuery(self._store, self._filters, (field, direction), self._limit_n)

    def limit(self, n: int) -> "FakeQuery":
        return FakeQuery(self._store, self._filters, self._order, n)

    def stream(self):
        items = list(self._store.docs.items())
        for field, op, value in self._filters:
            items = [(doc_id, data) for doc_id, data in items if _matches(data.get(field), op, value)]
        if self._order is not None:
            field, direction = self._order
            items.sort(key=lambda kv: (kv[1].get(field) is None, kv[1].get(field)), reverse=(direction == "DESCENDING"))
        if self._limit_n is not None:
            items = items[: self._limit_n]
        return [FakeDocSnapshot(doc_id, data) for doc_id, data in items]


class FakeCollection(FakeQuery):
    def __init__(self, store: FakeCollectionStore):
        super().__init__(store)

    def document(self, doc_id: str | None = None) -> FakeDocRef:
        return FakeDocRef(self._store, doc_id or str(uuid.uuid4()))


class FakeFirestoreClient:
    def __init__(self):
        self._collections: dict[str, FakeCollectionStore] = {}

    def collection(self, name: str) -> FakeCollection:
        store = self._collections.setdefault(name, FakeCollectionStore())
        return FakeCollection(store)
