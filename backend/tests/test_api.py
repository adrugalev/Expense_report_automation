from __future__ import annotations

from datetime import date
from io import BytesIO

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

    employees = authenticated_client.get("/api/employees")
    assert employees.status_code == 200
    assert len(employees.json()) == 6

    dashboard = authenticated_client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["employees_total"] == 6


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


def test_generate_gift_report_and_download(authenticated_client: TestClient) -> None:
    employees = authenticated_client.get("/api/employees").json()
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

    download = authenticated_client.get(report["files"][0]["download_url"])
    assert download.status_code == 200
    document = Document(BytesIO(download.content))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "1 250" in text
    assert date.today().strftime("%d.%m.%Y") in text

    archive = authenticated_client.get(f"/api/reports/{report['id']}/files.zip")
    assert archive.status_code == 200
    assert archive.content.startswith(b"PK")

    history = authenticated_client.get("/api/reports")
    assert history.status_code == 200
    assert any(item["id"] == report["id"] for item in history.json()["items"])


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
