# Отчёт о миграции

## Legacy Streamlit

Исходное приложение находится в `app.py`, стандартный cloud-entrypoint — `streamlit_app.py`. Оно поддерживает выбор типа отчёта и сотрудника, OCR/QR/PDF-разбор чеков, редактирование таблицы, формы трёх сценариев, автозаполнение представительских расходов, генерацию DOCX и ZIP. Legacy UI и привычная команда запуска сохранены.

## Modern Web

Новая версия построена рядом с legacy:

- Next.js/React/TypeScript frontend без Streamlit;
- FastAPI REST API с OpenAPI;
- SQLAlchemy и Alembic;
- SQLite для локальной разработки, PostgreSQL в Docker/production;
- Argon2 password hashing и JWT в HttpOnly cookie;
- роли `admin` и `employee` с привязкой учётной записи сотрудника к его карточке;
- постоянная история отчётов и файлов;
- общий Python core для обоих интерфейсов.

## Functional Parity Matrix

| Функция | Streamlit | New Web | Backend API | Статус |
| --- | --- | --- | --- | --- |
| Командировка | Да | Да | `POST /api/reports/generate` | Migrated |
| Представительские расходы | Да | Да | `POST /api/reports/generate` | Migrated |
| Один комплект по всем чекам | Да | Да | `build_mode=single` | Migrated |
| Комплект на каждый чек | Да | Да | `build_mode=per_receipt` | Migrated |
| Разные организации по чекам | Да | Да | `build_mode=per_receipt_different_companies` | Migrated |
| Подарки | Да | Да | `POST /api/reports/generate` | Migrated |
| Выбор сотрудника | Да | Admin: поиск; employee: только собственная карточка | `GET /api/employees` | Improved |
| Справочник сотрудников | JSON | CRUD + БД | `/api/employees` | Improved |
| Загрузка PDF/JPG/PNG | Да | Drag & drop, статусы, удаление | `/api/uploads` | Improved |
| OCR русского текста | Сервер PaddleOCR | Сервер FastAPI/Docker | Upload service | Improved |
| Проверка MIME/magic/размера | Частично | Да | Upload service | Improved |
| Редактирование чеков | Да | Да, TanStack Table | Typed report payload | Migrated |
| Ручная строка чека | Да | Да | Typed report payload | Migrated |
| Автоподстановка дат | Да | Да | Frontend + core validation | Migrated |
| Автозаполнение представительских | Да | Да | `/api/reports/suggestions/representative` | Migrated |
| DOCX generation | Да | Да | Shared core | Migrated |
| ZIP всех файлов | Да | Да | `GET /api/reports/{id}/files.zip` | Migrated |
| Предупреждения генератора | Да | Да | `warnings` в detail | Migrated |
| Черновик формы | Session state | Persistent browser draft | Frontend | Improved |
| История отчётов | Нет | Да | `GET /api/reports` | Improved |
| Авторизация и роли | Нет | Да | `/api/auth/*` | Improved |
| Пароли сотрудников | Нет | Управление администратором | `/api/accounts/employees/*` | Improved |
| Light/Dark/System | Нет | Да | Frontend | Improved |
| Mobile/tablet UI | Ограниченно | Да | Frontend | Improved |
| Загрузка DOCX-шаблонов из UI | Фактически отсутствует | Нет | Нет | Legacy documentation only |
| Установка OCR кнопкой | Нет | Не нужна в Docker | Нет | Removed |

## Improved

- Страницы и навигация без полного rerun Python-приложения.
- Форма не теряется при переходе назад или обновлении страницы.
- Загрузка асинхронная; повторная генерация блокируется на время запроса.
- Отчёты и справочники сохраняются между перезапусками.
- Файлы изолированы по пользователю/отчёту, имена и пути проверяются.
- Обзор и общая история доступны только администратору; employee account не может сформировать отчёт за другого сотрудника даже прямым API-запросом.
- Администратор связан с карточкой Другалёва; email из справочника является логином для обеих ролей.
- OCR выполняется централизованно через русскую модель PaddleOCR PP-OCRv5; установка на клиентских компьютерах не требуется.
- Ошибки API структурированы, frontend показывает inline validation, loading/empty/error states и краткие toast-сообщения.

## Pending

- Отключение учётных записей сотрудников через UI; создание доступа и смена пароля уже доступны администратору.
- Object storage для горизонтального масштабирования.
- Антивирусный scanner и автоматическая политика удаления старых uploads.
- Фоновая очередь для очень больших пакетов; текущая генерация выполняется в thread pool.
- Автогенерация TypeScript-моделей из OpenAPI; текущие модели типизированы вручную и проверяются сборкой/E2E.

## Known Differences

- Web-версия хранит сотрудников в БД после первоначального импорта; изменение `data/employees.json` не перезаписывает существующую БД.
- Web-версия хранит generated files в `STORAGE_DIR`, legacy — в `output/`.
- Runtime-кнопка установки OCR отсутствует: production image уже содержит PaddleOCR и локальные модели.
- Ручной ввод остаётся доступным, если исходный скан не позволяет надёжно распознать отдельные поля.

## Verification

- Shared/legacy pytest проверяет модели, парсер, шаблоны, document context и Streamlit helpers.
- Backend pytest проверяет auth, разделение ролей, смену пароля, запрет истории сотруднику, CRUD, uploads, все типы/режимы, скачивание DOCX и ZIP.
- Vitest проверяет frontend utilities и компоненты.
- Playwright проверяет вход, навигацию и полный сценарий формирования документа.
- Production Next.js build выполняет TypeScript validation всех маршрутов.
- Финальный HTTP smoke проверяет frontend и API через same-origin proxy.
- Compose YAML проверен структурно; image build не выполнялся, потому что на текущем host нет Docker Engine.
- Сгенерированный DOCX проверен как OOXML/ZIP и через извлечение текста/таблицы; визуальный DOCX-render недоступен без LibreOffice или Word на host.
- Внешний HTTPS-маршрут через Cloudflare Quick Tunnel проверен login/API/DOCX generation; ссылка временная и зависит от работающего локального host.
- Публичное разграничение admin/employee проверено API и 12 Playwright-сценариями на desktop/tablet/mobile; frontend работает из production build.
