from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..database_models import UserRecord
from ..dependencies import get_current_user, require_roles
from ..schemas.employee import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from ..services.employee_service import EmployeeConflictError, EmployeeNotFoundError, EmployeeService


router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeResponse])
def list_employees(
    session: Session = Depends(get_db),
    user: UserRecord = Depends(get_current_user),
) -> list[EmployeeResponse]:
    service = EmployeeService(session)
    if user.role == "admin":
        return service.list()
    if not user.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Учётная запись не связана с сотрудником")
    try:
        return [service.get(user.employee_id)]
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Карточка сотрудника не найдена") from exc


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    data: EmployeeCreate,
    session: Session = Depends(get_db),
    _user: UserRecord = Depends(require_roles("admin")),
) -> EmployeeResponse:
    try:
        return EmployeeService(session).create(data)
    except EmployeeConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: str,
    data: EmployeeUpdate,
    session: Session = Depends(get_db),
    _user: UserRecord = Depends(require_roles("admin")),
) -> EmployeeResponse:
    try:
        return EmployeeService(session).update(employee_id, data)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден") from exc
    except EmployeeConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: str,
    session: Session = Depends(get_db),
    _user: UserRecord = Depends(require_roles("admin")),
) -> Response:
    try:
        EmployeeService(session).delete(employee_id)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден") from exc
    except EmployeeConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
