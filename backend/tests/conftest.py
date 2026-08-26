from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


TEST_ROOT = Path(tempfile.gettempdir()) / f"expense-report-api-{uuid4()}"
TEST_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": f"sqlite:///{(TEST_ROOT / 'test.db').as_posix()}",
        "STORAGE_DIR": str(TEST_ROOT / "storage"),
        "SECRET_KEY": "test-secret-key-with-sufficient-length",
        "ADMIN_EMAIL": "aleksandr.drugalev@h-xgroup.com",
        "ADMIN_PASSWORD": "TestPassword123!",
        "ADMIN_NAME": "Другалев Александр Александрович",
        "ADMIN_EMPLOYEE_ID": "drugalev",
        "EMPLOYEE_ID": "baranova",
        "EMPLOYEE_PASSWORD": "EmployeeTest123!",
        "TRUSTED_HOSTS": "testserver,localhost,127.0.0.1",
    }
)

from backend.app.database import engine  # noqa: E402
from backend.app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture()
def authenticated_client(client: TestClient) -> TestClient:
    response = client.post(
        "/api/auth/login",
        json={"email": "aleksandr.drugalev@h-xgroup.com", "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return client
