from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps.auth import get_current_app_user
from app.db.session import get_db
from app.main import app
from app.models.user import AppUser


class FakeScalarResult:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def first(self) -> Any | None:
        return self._items[0] if self._items else None

    def all(self) -> list[Any]:
        return list(self._items)


class FakeResult:
    def __init__(self, *, rows: list[Any] | None = None, scalars: list[Any] | None = None) -> None:
        self._rows = rows or []
        self._scalars = scalars or []

    def first(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._scalars)


class FakeAsyncSession:
    def __init__(self) -> None:
        self.users: dict[UUID, AppUser] = {}

    def add(self, item: Any) -> None:
        now = datetime.now(UTC)
        if hasattr(item, "id") and getattr(item, "id", None) is None:
            setattr(item, "id", uuid4())
        if hasattr(item, "created_at") and getattr(item, "created_at", None) is None:
            setattr(item, "created_at", now)

        if isinstance(item, AppUser):
            self.users[item.id] = item

    async def commit(self) -> None:
        return None

    async def refresh(self, item: Any) -> None:
        return None

    async def execute(self, stmt: Any) -> FakeResult:
        entity = stmt.column_descriptions[0].get("entity")
        if entity is AppUser:
            return FakeResult(rows=list(self.users.values()), scalars=list(self.users.values()))
        return FakeResult(rows=[], scalars=[])

    async def execute(self, stmt: Any) -> Any:
        class MockResult:
            def scalars(self): return self
            def first(self): return None
            def all(self): return []
            def __iter__(self): return iter([])
        return MockResult()

    async def get(self, model: type[Any], item_id: UUID) -> Any | None:
        if model is AppUser:
            return self.users.get(item_id)
        return None


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _override_db(fake_db: FakeAsyncSession):
    async def _dependency():
        yield fake_db

    return _dependency


def _user(
    *,
    user_id: UUID | None = None,
    clerk_user_id: str = "clerk_user_1",
    display_name: str | None = "Test User",
) -> AppUser:
    return AppUser(
        id=user_id or uuid4(),
        clerk_user_id=clerk_user_id,
        display_name=display_name,
        created_at=datetime.now(UTC),
    )


def test_users_me_and_compatibility_endpoints(client: TestClient) -> None:
    fake_db = FakeAsyncSession()
    current_user = _user(display_name="Original")

    app.dependency_overrides[get_db] = _override_db(fake_db)
    app.dependency_overrides[get_current_app_user] = lambda: current_user

    me_response = client.get("/v1/users/me")
    assert me_response.status_code == 200
    assert me_response.json()["id"] == str(current_user.id)

    patch_response = client.patch("/v1/users/me", json={"display_name": "Updated"})
    assert patch_response.status_code == 200
    assert patch_response.json()["display_name"] == "Updated"

    compat_response = client.get(f"/v1/users/{current_user.id}")
    assert compat_response.status_code == 200

    mismatch_response = client.get(f"/v1/users/{uuid4()}")
    assert mismatch_response.status_code == 403

    clerk_response = client.get(f"/v1/users/clerk/{current_user.clerk_user_id}")
    assert clerk_response.status_code == 200
