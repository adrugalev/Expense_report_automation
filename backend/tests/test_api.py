from __future__ import annotations

from datetime import date
from io import BytesIO
import time

from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter


def test_health_and_openapi_are_public(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert "/api/reports/generate" in openapi.json()["paths"]


def test_login_dashboard_and_seeded_employees(authenticated_client: TestClient) -> None:
    me = authenticated_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "admin"
    assert me.json()["email"] == "aleksandr.drugalev@h-xgroup.com"
    assert me.json()["full_name"] == "Другалев Александр Александрович"
    assert me.json()["employee_id"] == "drugalev"

    employees = authenticated_client.get("/api/employees")
    assert employees.status_code == 200
    assert len(employees.json()) == 6

    dashboard = authenticated_client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["employees_total"] == 6


def test_admin_changes_own_password(authenticated_client: TestClient) -> None:
    changed_password = "ChangedAdminPassword123!"

    wrong_current = authenticated_client.put(
        "/api/auth/password",
        json={"current_password": "WrongPassword123!", "new_password": changed_password},
    )
    assert wrong_current.status_code == 400
    assert "Текущий пароль" in wrong_current.json()["detail"]

    same_password = authenticated_client.put(
        "/api/auth/password",
        json={"current_password": "TestPassword123!", "new_password": "TestPassword123!"},
    )
    assert same_password.status_code == 400

    changed = authenticated_client.put(
        "/api/auth/password",
        json={"current_password": "TestPassword123!", "new_password": changed_password},
    )
    assert changed.status_code == 204

    assert authenticated_client.post("/api/auth/logout").status_code == 204
    old_login = authenticated_client.post(
        "/api/auth/login",
        json={"email": "aleksandr.drugalev@h-xgroup.com", "password": "TestPassword123!"},
    )
    assert old_login.status_code == 401
    new_login = authenticated_client.post(
        "/api/auth/login",
        json={"email": "aleksandr.drugalev@h-xgroup.com", "password": changed_password},
    )
    assert new_login.status_code == 200

    restored = authenticated_client.put(
        "/api/auth/password",
        json={"current_password": changed_password, "new_password": "TestPassword123!"},
    )
    assert restored.status_code == 204


def test_admin_manages_employee_password_and_employee_access_is_restricted(
    authenticated_client: TestClient,
) -> None:
    employees = authenticated_client.get("/api/employees").json()
    own_employee = next(item for item in employees if item["id"] == "baranova")
    other_employee = next(item for item in employees if item["id"] != "baranova")

    accounts = authenticated_client.get("/api/accounts/employees")
    assert accounts.status_code == 200
    admin_account = next(item for item in accounts.json() if item["employee_id"] == "drugalev")
    assert admin_account["role"] == "admin"
    assert authenticated_client.put(
        "/api/accounts/employees/drugalev/password",
        json={"password": "MustNotReplaceAdmin123!"},
    ).status_code == 409
    own_account = next(item for item in accounts.json() if item["employee_id"] == "baranova")
    assert own_account["role"] == "employee"
    assert own_account["has_account"] is True
    assert own_account["email"] == own_employee["email"]

    changed_password = "ChangedEmployee123!"
    reset = authenticated_client.put(
        "/api/accounts/employees/baranova/password",
        json={"password": changed_password},
    )
    assert reset.status_code == 200
    assert reset.json()["has_account"] is True

    assert authenticated_client.post("/api/auth/logout").status_code == 204
    login = authenticated_client.post(
        "/api/auth/login",
        json={"email": own_employee["email"], "password": changed_password},
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "employee"
    assert login.json()["user"]["employee_id"] == "baranova"

    assert authenticated_client.get("/api/dashboard").status_code == 403
    assert authenticated_client.get("/api/reports").status_code == 403
    assert authenticated_client.get("/api/accounts/employees").status_code == 403
    visible_employees = authenticated_client.get("/api/employees")
    assert visible_employees.status_code == 200
    assert [item["id"] for item in visible_employees.json()] == ["baranova"]

    report_date = date.today().isoformat()
    base_request = {
        "report_type": "gifts",
        "report_date": report_date,
        "receipts": [{
            "file_name": "employee-gift.pdf",
            "date": report_date,
            "seller": "Подарочный магазин",
            "amount": "500.00",
            "expense_type": "подарки",
        }],
        "purchase_date": report_date,
        "gift_name": "подарочная продукция",
        "gift_quantity": 1,
        "unit_price": "500.00",
        "recipients": [],
        "counterparty": "Подарки",
        "occasion": "",
        "purpose": "Укрепление деловых отношений",
        "build_mode": "single",
    }
    forbidden = authenticated_client.post(
        "/api/reports/generate",
        json={**base_request, "employee_id": other_employee["id"]},
    )
    assert forbidden.status_code == 403
    assert "только для себя" in forbidden.json()["detail"]

    generated = authenticated_client.post(
        "/api/reports/generate",
        json={**base_request, "employee_id": "baranova"},
    )
    assert generated.status_code == 201, generated.text
    report = generated.json()
    assert report["employee_id"] == "baranova"
    assert authenticated_client.get(f"/api/reports/{report['id']}").status_code == 200
    assert authenticated_client.delete(f"/api/reports/{report['id']}").status_code == 403

    assert authenticated_client.post("/api/auth/logout").status_code == 204
    admin_login = authenticated_client.post(
        "/api/auth/login",
        json={"email": "aleksandr.drugalev@h-xgroup.com", "password": "TestPassword123!"},
    )
    assert admin_login.status_code == 200
    history = authenticated_client.get("/api/reports")
    assert history.status_code == 200
    assert any(item["id"] == report["id"] for item in history.json()["items"])


def test_employee_crud(authenticated_client: TestClient) -> None:
    create = authenticated_client.post(
        "/api/employees",
        json={
            "id": "web-test-user",
            "full_name": "Тестов Тест Тестович",
            "position": "Менеджер",
            "department": "Продажи",
            "company": "ООО Тест",
            "email": "test@example.com",
        },
    )
    assert create.status_code == 201
    assert create.json()["id"] == "web-test-user"

    update_payload = create.json()
    update_payload.pop("id")
    update_payload["position"] = "Старший менеджер"
    update = authenticated_client.put("/api/employees/web-test-user", json=update_payload)
    assert update.status_code == 200
    assert update.json()["position"] == "Старший менеджер"

    delete = authenticated_client.delete("/api/employees/web-test-user")
    assert delete.status_code == 204


def test_representative_suggestions_rotate_counterparties_and_participants(
    authenticated_client: TestClient,
) -> None:
    recent: list[str] = []
    previous_participants: list[str] | None = None
    previous_purpose: str | None = None
    previous_result: str | None = None

    for _ in range(5):
        response = authenticated_client.post(
            "/api/reports/suggestions/representative",
            json={
                "signature": "Ресторан Тест Москва",
                "recent_counterparties": recent[-3:],
                "meeting_purpose": "",
            },
        )
        assert response.status_code == 200
        suggestion = response.json()
        assert suggestion["counterparty"] not in recent[-3:]
        assert suggestion["participants_counterparty"]
        assert "\u043b\u0438\u0444\u0442" in suggestion["meeting_purpose"].lower()
        if previous_participants is not None:
            assert suggestion["participants_counterparty"] != previous_participants
            assert suggestion["meeting_purpose"] != previous_purpose
            assert suggestion["meeting_result"] != previous_result
        recent.append(suggestion["counterparty"])
        previous_participants = suggestion["participants_counterparty"]
        previous_purpose = suggestion["meeting_purpose"]
        previous_result = suggestion["meeting_result"]


def test_upload_rejects_fake_pdf(authenticated_client: TestClient) -> None:
    response = authenticated_client.post(
        "/api/uploads/receipts",
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )
    assert response.status_code == 422
    assert "не соответствует" in response.json()["detail"]


def test_upload_accepts_and_deletes_real_pdf(authenticated_client: TestClient) -> None:
    payload = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(payload)
    response = authenticated_client.post(
        "/api/uploads/receipts",
        files={"file": ("receipt.pdf", payload.getvalue(), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    upload = response.json()
    assert upload["mime_type"] == "application/pdf"
    assert upload["receipt"]["file_name"] == "receipt.pdf"
    assert authenticated_client.delete(f"/api/uploads/{upload['id']}").status_code == 204


def test_receipt_job_reports_progress_and_result(authenticated_client: TestClient) -> None:
    payload = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(payload)

    started = authenticated_client.post(
        "/api/uploads/receipts/jobs",
        files={"file": ("progress.pdf", payload.getvalue(), "application/pdf")},
    )

    assert started.status_code == 202, started.text
    for _ in range(100):
        job = authenticated_client.get(f"/api/uploads/receipts/jobs/{started.json()['job_id']}")
        assert job.status_code == 200
        if job.json()["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)
    assert job.json()["status"] == "completed"
    assert job.json()["progress"] == 100
    assert job.json()["stage"] == "Готово"
    upload = job.json()["result"]
    assert upload["receipt"]["file_name"] == "progress.pdf"
    assert authenticated_client.delete(f"/api/uploads/{upload['id']}").status_code == 204


def test_generate_gift_report_and_download(authenticated_client: TestClient) -> None:
    employees = authenticated_client.get("/api/employees").json()
    receipt_payload = BytesIO()
    receipt_writer = PdfWriter()
    receipt_writer.add_blank_page(width=100, height=100)
    receipt_writer.write(receipt_payload)
    receipt_bytes = receipt_payload.getvalue()
    uploaded = authenticated_client.post(
        "/api/uploads/receipts",
        files={"file": ("gift.pdf", receipt_bytes, "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    upload = uploaded.json()
    request = {
        "report_type": "gifts",
        "employee_id": employees[0]["id"],
        "report_date": date.today().isoformat(),
        "receipts": [
            {
                "file_name": "gift.pdf",
                "date": date.today().isoformat(),
                "seller": "Подарочный магазин",
                "amount": "1250.50",
                "expense_type": "подарки",
            }
        ],
        "receipt_uploads": [{"upload_id": upload["id"], "receipt_index": 0}],
        "purchase_date": date.today().isoformat(),
        "gift_name": "подарочная продукция",
        "gift_quantity": 1,
        "unit_price": "1250.50",
        "recipients": [],
        "counterparty": "Подарки",
        "occasion": "",
        "purpose": "Укрепление деловых отношений",
        "build_mode": "single",
    }
    generated = authenticated_client.post("/api/reports/generate", json=request)
    assert generated.status_code == 201, generated.text
    report = generated.json()
    assert report["status"] == "completed"
    assert len(report["files"]) == 1
    assert len(report["receipt_files"]) == 1
    assert report["receipt_files"][0]["name"] == "gift.pdf"
    assert report["receipt_files"][0]["amount"] == "1250.50"

    download = authenticated_client.get(report["files"][0]["download_url"])
    assert download.status_code == 200
    document = Document(BytesIO(download.content))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "1 250" in text
    assert date.today().strftime("%d.%m.%Y") in text

    receipt_url = report["receipt_files"][0]["download_url"]
    assert authenticated_client.delete(f"/api/uploads/{upload['id']}").status_code == 204
    receipt_download = authenticated_client.get(receipt_url)
    assert receipt_download.status_code == 200
    assert receipt_download.content == receipt_bytes

    archive = authenticated_client.get(f"/api/reports/{report['id']}/files.zip")
    assert archive.status_code == 200
    assert archive.content.startswith(b"PK")

    history = authenticated_client.get("/api/reports")
    assert history.status_code == 200
    assert any(item["id"] == report["id"] for item in history.json()["items"])

    delete = authenticated_client.delete(f"/api/reports/{report['id']}")
    assert delete.status_code == 204
    assert authenticated_client.get(f"/api/reports/{report['id']}").status_code == 404
    assert authenticated_client.get(report["files"][0]["download_url"]).status_code == 404
    assert authenticated_client.get(receipt_url).status_code == 404
    history_after_delete = authenticated_client.get("/api/reports")
    assert all(item["id"] != report["id"] for item in history_after_delete.json()["items"])


def test_generate_business_trip_report(authenticated_client: TestClient) -> None:
    employee_id = authenticated_client.get("/api/employees").json()[0]["id"]
    current_date = date.today().isoformat()
    generated = authenticated_client.post(
        "/api/reports/generate",
        json={
            "report_type": "business_trip",
            "employee_id": employee_id,
            "report_date": current_date,
            "receipts": [{
                "file_name": "taxi.pdf",
                "date": current_date,
                "seller": "Яндекс Такси",
                "amount": "980.00",
                "expense_type": "такси",
                "route": "Аэропорт - офис",
            }],
            "trip_city": "Москва",
            "trip_start_date": current_date,
            "trip_end_date": current_date,
            "purpose": "Встреча с клиентом",
            "build_mode": "single",
        },
    )
    assert generated.status_code == 201, generated.text
    report = generated.json()
    assert report["status"] == "completed"
    assert report["total_amount"] == "980.00"
    assert report["files"]


def test_generate_representative_reports_in_all_modes(authenticated_client: TestClient) -> None:
    employee_id = authenticated_client.get("/api/employees").json()[0]["id"]
    current_date = date.today().isoformat()
    receipts = [
        {
            "file_name": f"restaurant-{index}.pdf",
            "date": current_date,
            "seller": f"Ресторан {index}",
            "address": f"г. Москва, ул. Тестовая, д. {index}",
            "amount": str(1000 * index),
            "expense_type": "ресторан",
        }
        for index in (1, 2)
    ]
    for mode in ("single", "per_receipt", "per_receipt_different_companies"):
        generated = authenticated_client.post(
            "/api/reports/generate",
            json={
                "report_type": "representative_expenses",
                "employee_id": employee_id,
                "report_date": current_date,
                "receipts": receipts,
                "event_date": current_date,
                "place": "г. Москва",
                "restaurant_name": "Тестовый ресторан",
                "counterparty": "ООО Контрагент",
                "meeting_purpose": "Обсуждение сотрудничества",
                "participants_company": ["Баранова Гиляна Басанговна"],
                "participants_counterparty": ["Иванов Иван Иванович"],
                "meeting_result": "Согласованы дальнейшие действия",
                "build_mode": mode,
            },
        )
        assert generated.status_code == 201, generated.text
        report = generated.json()
        assert report["status"] == "completed"
        assert report["total_amount"] == "3000"
        assert report["files"], mode


def test_business_trip_rejects_receipt_outside_trip(authenticated_client: TestClient) -> None:
    employee_id = authenticated_client.get("/api/employees").json()[0]["id"]
    generated = authenticated_client.post(
        "/api/reports/generate",
        json={
            "report_type": "business_trip",
            "employee_id": employee_id,
            "report_date": "2026-08-25",
            "receipts": [{"file_name": "taxi.pdf", "date": "2026-08-10", "amount": "100", "expense_type": "такси"}],
            "trip_city": "Москва",
            "trip_start_date": "2026-08-20",
            "trip_end_date": "2026-08-21",
            "purpose": "Встреча",
            "build_mode": "single",
        },
    )
    assert generated.status_code == 422
    assert "период командировки" in generated.json()["detail"]
