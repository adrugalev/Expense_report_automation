# Автоматизация отчётных документов

Система формирует DOCX-комплекты по командировкам, представительским расходам и подаркам. В репозитории работают два интерфейса над общей Python-бизнес-логикой:

- современное web-приложение: Next.js + FastAPI;
- исходное Streamlit-приложение как legacy/fallback.

Web-версия включает авторизацию, роли, постоянную историю отчётов, CRUD сотрудников, загрузку и OCR чеков, редактирование распознанных данных, генерацию DOCX и скачивание ZIP. OCR выполняется на сервере: пользователям браузера не нужны Python, Tesseract или другие локальные программы.

## Быстрый запуск через Docker

Требуются Docker Engine и Docker Compose.

```bash
cp .env.example .env
# Замените пароли и SECRET_KEY в .env
docker compose up --build -d
```

Откройте `http://localhost:3000`. Начальные учётные данные берутся из `ADMIN_EMAIL` и `ADMIN_PASSWORD` в `.env`.

Контейнеры:

- `frontend`: production-сборка Next.js, порт 3000;
- `backend`: FastAPI, OCR, Tesseract `rus+eng`, Poppler и ZBar;
- `db`: PostgreSQL 17;
- `report_storage`: загруженные чеки и сформированные документы;
- `postgres_data`: постоянные данные приложения.

Остановка: `docker compose down`. Данные сохраняются в Docker volumes. Команда `docker compose down -v` удаляет их и должна использоваться только осознанно.

## Локальная разработка

### Backend

Нужен Python 3.12+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e ".\backend[test]"
alembic -c backend/alembic.ini upgrade head
python -m uvicorn backend.app.main:app --reload --port 8000
```

По умолчанию backend использует SQLite в `storage/expense_web.db`. API: `http://localhost:8000/api/health`; OpenAPI: `http://localhost:8000/docs`.

Для OCR сканов при локальном запуске backend установите Tesseract с русским и английским языками и Poppler. В Docker они уже включены.

### Frontend

Нужны Node.js 22+ и pnpm.

```powershell
cd frontend
corepack enable
pnpm install
pnpm dev
```

Откройте `http://localhost:3000`. Next.js проксирует `/api/*` на `http://127.0.0.1:8000`. Другой backend задаётся через `BACKEND_INTERNAL_URL`.

Начальная dev-учётная запись: `admin@example.com` / `ChangeMe123!`. Она создаётся только в пустой БД; для общей или production-среды обязательно задайте собственные значения.

## Legacy Streamlit

Старое приложение сохранено без изменения команды запуска:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Альтернативный entrypoint для Streamlit Cloud: `streamlit run streamlit_app.py`. Обычно legacy-интерфейс доступен по адресу `http://localhost:8501`. Он продолжает использовать `data/employees.json`, `templates/` и `output/`.

## Архитектура

```text
Browser -> Next.js -> FastAPI -> shared src/ -> DOCX / OCR
                         |             |
                         v             v
                    PostgreSQL      templates/

Legacy Streamlit -----------------> shared src/
```

- `frontend/`: Next.js App Router, React, TypeScript, Tailwind, TanStack Query/Table, React Hook Form, Zod.
- `backend/`: FastAPI routes, Pydantic-схемы, service layer, SQLAlchemy, Alembic, JWT-cookie auth.
- `src/`: общие модели, парсер чеков, OCR, генераторы DOCX и оркестрация отчётов.
- `templates/`: существующие DOCX-шаблоны.
- `data/`: исходный справочник сотрудников и профили автозаполнения.
- `storage/`: локальная SQLite, uploads и результаты web-версии; не коммитится.
- `app.py`: legacy Streamlit UI.

Подробности и диаграмма: [ARCHITECTURE.md](ARCHITECTURE.md). Результаты миграции: [MIGRATION_REPORT.md](MIGRATION_REPORT.md).

## Пользовательский сценарий

1. Войдите в систему.
2. Откройте «Новый отчёт» и выберите тип.
3. Найдите сотрудника по ФИО или должности.
4. Перетащите PDF/JPG/PNG чеки или добавьте строку вручную.
5. Проверьте дату, продавца, адрес, ИНН, сумму и ФД.
6. Заполните поля выбранного типа отчёта.
7. Сформируйте документы и скачайте DOCX либо общий ZIP.
8. Повторно открыть результат можно из «Истории».

Черновик формы сохраняется в браузере до успешного формирования или ручной очистки.

## Справочник сотрудников

Начальные сотрудники импортируются из `data/employees.json` при создании пустой БД. После этого web-версия хранит справочник в БД. Администратор может создавать, редактировать и удалять записи в разделе «Справочники». Выбранный профиль автоматически передаётся генератору документов.

## Шаблоны документов

Существующие шаблоны не перемещались: `templates/business_trip/`, `templates/representative_expenses/`, `templates/gifts/`.

Генерация остаётся на Python и использует `docxtpl`/`python-docx`. Web frontend не генерирует и не изменяет DOCX. Представительские расходы и подарки сохраняют программные генераторы legacy-проекта; командировка использует существующие шаблоны.

## Конфигурация

Backend читает корневой `.env` и `backend/.env`.

| Переменная | Назначение | Dev default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy URL | SQLite в `storage/` |
| `SECRET_KEY` | подпись JWT | только dev-значение |
| `ADMIN_EMAIL` | первый администратор | `admin@example.com` |
| `ADMIN_PASSWORD` | пароль первого администратора | `ChangeMe123!` |
| `STORAGE_DIR` | uploads и результаты | `storage/` |
| `TEMPLATES_DIR` | DOCX-шаблоны | `templates/` |
| `LEGACY_DATA_DIR` | начальные JSON-данные | `data/` |
| `MAX_UPLOAD_SIZE` | предел файла в байтах | 15 МБ |
| `ALLOWED_ORIGINS` | CORS allowlist | localhost:3000 |
| `TRUSTED_HOSTS` | допустимые Host headers | localhost |
| `COOKIE_SECURE` | Secure cookie | `false` |

В production используйте длинный случайный `SECRET_KEY`, сильные пароли, `COOKIE_SECURE=true`, конкретные HTTPS origin/host и резервное копирование обоих volumes.

## База данных и миграции

Локально допустима SQLite, в Docker и production используется PostgreSQL. Схема управляется Alembic:

```powershell
alembic -c backend/alembic.ini upgrade head
alembic -c backend/alembic.ini current
```

В БД хранятся пользователи, сотрудники, метаданные загрузок, отчёты и сформированные файлы. Сами бинарные файлы находятся в `STORAGE_DIR`; для нескольких экземпляров backend потребуется общее object/file storage.

## Тесты

```powershell
# Legacy и shared core
pytest

# Backend API и generation pipeline
pytest backend/tests

# Frontend
cd frontend
pnpm test
pnpm lint
pnpm build

# E2E при запущенных backend и frontend
pnpm exec playwright install chromium
pnpm test:e2e
```

## Развёртывание на Linux VPS

1. Установите Docker Engine и Compose plugin.
2. Клонируйте репозиторий и создайте `.env` из `.env.example`.
3. Задайте секреты, `COOKIE_SECURE=true` и выполните `docker compose up --build -d`.
4. Разместите nginx/Caddy перед портом 3000 и выпустите TLS-сертификат.
5. Не публикуйте PostgreSQL и backend наружу; внешним должен быть только HTTPS frontend.
6. Настройте резервные копии `postgres_data` и `report_storage`, ротацию логов и мониторинг `/api/health`.
7. При масштабировании вынесите файлы в S3-совместимое хранилище и запускайте миграции один раз перед обновлением backend.

Схема: Internet -> HTTPS reverse proxy -> Next.js -> FastAPI -> PostgreSQL + file storage.

## Безопасность файлов

Backend проверяет расширение, MIME, magic bytes, максимальный размер, очищает имя файла и изолирует пользовательские каталоги. Разрешены PDF, PNG, JPG и JPEG. Пути скачивания проверяются относительно каталога отчётов. Для публичного сервиса дополнительно рекомендуется антивирусная проверка uploads и политика срока хранения.

## Миграция

Streamlit не используется ни frontend, ни FastAPI. Общие модули `src/` не зависят от UI. `app.py` сохранён и продолжает обращаться к тому же core. Никакие шаблоны и исходные данные не удалены. Полная матрица функций и известные различия находятся в [MIGRATION_REPORT.md](MIGRATION_REPORT.md).
