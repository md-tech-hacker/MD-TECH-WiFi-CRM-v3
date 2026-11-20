import pytest
from fastapi.testclient import TestClient
import app.db as storage
import app.security as security
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'test.sqlite3')
    monkeypatch.setattr(storage, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(security, 'DATA_DIR', tmp_path)
    security._attempts.clear()
    with TestClient(app, client=('127.0.0.1', 50000)) as c:
        yield c


@pytest.fixture()
def admin(client):
    response = client.post('/api/auth/setup', json={'username': 'admin', 'password': 'VeryStrongAdminSecret17!'})
    assert response.status_code == 200, response.text
    return {'X-CSRF-Token': response.json()['csrf']}
