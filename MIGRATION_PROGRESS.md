# Migration Progress

## 1. Цель миграции

- Сохранить существующее Streamlit-приложение рабочим как legacy/fallback.
- Создать рядом независимую web-версию: FastAPI backend и Next.js/React/TypeScript frontend.
- Максимально переиспользовать проверенную Python-бизнес-логику и отделить её от UI.
- Сохранить OCR чеков, три сценария отчётов, DOCX/ZIP generation, шаблоны и справочники.
- Подготовить persistent storage, authentication, tests, Docker и production-развёртывание.

## 2. Текущее состояние архитектуры

- Legacy UI: `app.py`, `streamlit_app.py`; команда запуска не менялась.
- Shared core: существующий `src/` плюс `src/report_orchestration.py` и `src/representative_autofill.py`.
- Backend: `backend/app/` с FastAPI routes, Pydantic schemas, services, SQLAlchemy, Alembic и Argon2/JWT auth.
- Frontend: `frontend/` с Next.js App Router, React, TypeScript, Tailwind, TanStack Query/Table, React Hook Form, Zod и react-dropzone.
- Persistence: SQLite в локальной разработке, PostgreSQL в Docker/production; бинарные файлы в `STORAGE_DIR`.
- Data/templates: `data/employees.json`, `data/representative_profiles.json`, существующие `templates/` без перемещения.
- Поток: Browser -> Next.js -> FastAPI -> shared `src/` -> OCR/DOCX; Streamlit также использует shared `src/`.

## 3. Уже выполнено

- [x] Проведён полный аудит legacy-проекта; результат в `docs/DISCOVERY_AUDIT.md`.
- [x] Созданы `ARCHITECTURE.md` с Mermaid-диаграммами и `MIGRATION_REPORT.md` с parity matrix.
- [x] Представительские профили и общая оркестрация вынесены из Streamlit в reusable core.
- [x] Создан FastAPI backend с `/api/health`, OpenAPI, auth, dashboard, employees, uploads и reports.
- [x] Реализованы Argon2 password hashes, JWT в HttpOnly cookie и роли admin/employee.
- [x] Учётная запись сотрудника связана с карточкой сотрудника; employee формирует отчёты только от своего имени.
- [x] Обзор и общая история закрыты для employee; администратор управляет паролями сотрудников в настройках.
- [x] Администратор связан с карточкой Другалёва; логином всех ролей является email из справочника.
- [x] Реализованы SQLAlchemy entities, SQLite/PostgreSQL configuration и начальная Alembic migration.
- [x] Реализована безопасная загрузка PDF/PNG/JPG: extension, MIME, magic bytes, size, safe path и delete.
- [x] Реализованы все три типа отчётов и три режима представительских документов.
- [x] Реализованы история, detail screen, DOCX download и ZIP download.
- [x] Создан responsive Next.js UI: login, dashboard, новый отчёт, история, справочник, settings.
- [x] Реализованы searchable employee picker, drag-and-drop, editable receipt table и per-user browser draft.
- [x] Реализованы light/dark/system theme, skeleton/empty/error states, toasts и confirmation dialog.
- [x] Созданы backend/frontend Dockerfiles, `docker-compose.yml`, healthchecks и `.env.example`.
- [x] PaddleOCR PP-OCRv5 для русского текста, локальные модели, Poppler и ZBar включены в backend Docker image.
- [x] README обновлён для web, legacy, Docker, development, tests и Linux VPS.
- [x] Backend/API regression tests охватывают auth, CRUD, uploads, DOCX/ZIP и все типы/режимы отчётов.
- [x] Vitest и Playwright tests добавлены; Playwright проверяет desktop/tablet/mobile и generation flow.
- [x] Legacy Streamlit healthcheck и новая web-версия ранее запускались успешно.

## 4. В работе

- Публичная demo-ссылка активна через Cloudflare Quick Tunnel; для постоянного uptime нужен named tunnel или PaaS/VPS аккаунт.

## 5. Осталось сделать

- [x] Выполнить полный Python pytest после обновления даты версии.
- [x] Выполнить frontend Vitest, ESLint и production build после последнего frontend patch.
- [x] Повторно выполнить полный Playwright suite на desktop/tablet/mobile.
- [x] Запустить backend/frontend и оставить локальный URL для проверки пользователем.
- [x] Проверить финальный `git diff --check`, status и отсутствие удаления legacy/templates/data.
- [x] Зафиксировать невозможность Docker build на текущем host без установленного Docker Engine.
- [x] Подготовить финальный отчёт с командами запуска и известными ограничениями.
- [ ] На host с Docker Engine выполнить production smoke: `docker compose up --build`.
- [x] Опубликовать текущий сервис по внешней HTTPS-ссылке и проверить полный публичный маршрут.
- [ ] Перенести сервис на постоянный URL с гарантированным uptime после предоставления hosting/domain credentials.

## 6. Архитектурные решения

- Существующий `src/` оставлен shared core вместо искусственного каталога `shared/`; это уменьшает риск регрессии legacy.
- DOCX generation остаётся полностью на Python; React передаёт только typed structured payload.
- Routes тонкие, значимая логика находится в services, Pydantic schemas задают public contracts.
- SQLite выбран для zero-config local dev, PostgreSQL — для production Compose.
- Файлы не хранятся в БД: БД содержит metadata, `STORAGE_DIR` — uploads/results.
- Next.js проксирует `/api/*`, поэтому browser работает same-origin и HttpOnly cookie не требует JS-доступа.
- Для online deployment добавлена минимальная authentication; роли заложены в model/API guards без избыточного RBAC.
- OCR централизован на backend; клиентским компьютерам не требуются Python и OCR-программы.
- PaddleOCR runtime и модели включены в Docker image заранее; runtime-установка из интерфейса удалена.
- Черновики разделены по user id в localStorage, чтобы пользователи одного браузера не видели общий draft.
- Синхронный Python generator выполняется через FastAPI thread pool; отдельная очередь не добавлена для текущих объёмов.

## 7. Обратная совместимость

- `app.py` и `streamlit_app.py` сохранены на прежних путях.
- Из `app.py` вынесены только представительские профили/автозаполнение и общие helper-функции; wrappers сохраняют прежние вызовы.
- `src/models.py`, receipt parser, report builders, template manager, `data/` и `templates/` не удалены.
- Legacy Streamlit ранее запущен на `:8501`; `/_stcore/health` вернул `200 ok`.
- Полный shared/legacy pytest ранее прошёл; известных legacy-регрессий нет.

## 8. Проверки и тесты

- `python -m pytest -q` после добавления смены пароля администратора: 105 passed, 8 skipped, 1 dependency deprecation warning.
- `python -m pytest backend/tests -q`: 12 passed.
- `pnpm test` после последних изменений: 5 passed.
- `pnpm lint` после добавления generated-artifact ignores: passed без warnings.
- `pnpm build` после последних изменений: passed; все application routes собраны, TypeScript passed.
- Публичный `pnpm test:e2e` версии 8: 18 passed (desktop, tablet, mobile, пустые цель/результат до нажатия «Я — Джон Сноу», ротация контрагентов и full gift-report flow).
- Backend role regression после добавления employee account: 10 passed; проверены смена пароля, запрет истории и формирование только за себя.
- Playwright overflow check выявил и подтвердил исправление wide-table grid overflow.
- UI screenshots вручную проверены на desktop/tablet/mobile; перекрытие sticky action bar исправлено.
- Alembic initial migration применена к чистой SQLite успешно.
- Реальный DOCX через web API: valid ZIP/DOCX, 10 paragraphs, 1 table, ожидаемые ФИО/дата/сумма.
- DOCX visual render не выполнен: на host отсутствуют LibreOffice и Microsoft Word; structural QA пройден.
- `docker-compose.yml` успешно разобран YAML parser; Docker build не запускался, Docker Engine отсутствует.
- Финальный HTTP smoke: frontend `/login` = 200, proxied `/api/health` = `ok`, `/api/meta` = `Версия 11 от 26.08.2026`.
- Финальный `git diff --check`: passed; legacy entrypoints и шаблоны всех трёх типов существуют.
- Cloudflare Quick Tunnel: публичная login page = 200, auth = success, employees = 6, report generation = completed/1 DOCX.
- Повторный внешний smoke после усиления конфигурации: health = `ok`, auth = 200, admin session = active, cookie содержит `HttpOnly`, `SameSite=Lax` и `Secure`.
- Публичный role smoke версии 3: admin dashboard/history = 200; employee dashboard/history/accounts = 403; employee видит одну собственную карточку и успешно формирует DOCX за себя.
- Публичный identity smoke версии 4: старый логин `admin@example.com` отклонён; `aleksandr.drugalev@h-xgroup.com` входит как администратор Другалёв с `employee_id=drugalev`; смена его пароля через управление сотрудниками заблокирована.
- Публичный representative-autofill smoke версии 5: повторное нажатие меняет контрагента и связанных с ним участников; проверено на desktop, tablet и mobile.
- Публичный password smoke версии 6: неверный текущий пароль отклонён; после смены старый пароль перестал работать, новый сработал; исходный рабочий пароль затем успешно восстановлен.
- Публичный form smoke версии 8: кнопка называется «Я — Джон Сноу»; цель и результат встречи пусты до нажатия и заполняются только после него.
- Публичный representative smoke версии 9: на desktop, tablet и mobile при смене контрагента меняются цель, результат и участники; textarea раскрываются до полной высоты без внутренней прокрутки.
- Публичный navigation smoke версии 10: `/` перенаправляет на `/reports/new`; «Обзор» отсутствует; название «Автоматизация отчётных документов» помещается в desktop, tablet и mobile sidebar.
- Публичный receipt-table smoke версии 11: до и после добавления строки горизонтальный overflow равен `0`; desktop использует компактную таблицу, tablet/mobile — вертикальную сетку полей.
- Публичный frontend переведён с `next dev` на production build, чтобы HTTPS-туннель стабильно отдавал JavaScript chunks.
- Публичный URL работает только пока запущены локальные backend, frontend и tunnel processes; Quick Tunnel не имеет SLA.

## 9. Следующий шаг

Публичная demo-ссылка готова к user acceptance; для постоянного адреса выбрать VPS/PaaS или предоставить Cloudflare account/domain.

## NEXT STEP

Подключить постоянный hosting/domain, развернуть `docker-compose.yml` или named Cloudflare Tunnel и повторить public smoke на постоянном URL.
