from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..database_models import UserRecord
from ..dependencies import require_roles
from ..schemas.account import EmployeeAccountResponse, EmployeePasswordUpdate
from ..services.account_service import AccountConflictError, AccountNotFoundError, AccountService


router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/employees", response_model=list[EmployeeAccountResponse])
def list_employee_accounts(
    session: Session = Depends(get_db),
    _admin: UserRecord = Depends(require_roles("admin")),
) -> list[EmployeeAccountResponse]:
    return AccountService(session).list_employee_accounts()


@router.put("/employees/{employee_id}/password", response_model=EmployeeAccountResponse)
def set_employee_password(
    employee_id: str,
    data: EmployeePasswordUpdate,
    session: Session = Depends(get_db),
    _admin: UserRecord = Depends(require_roles("admin")),
) -> EmployeeAccountResponse:
    try:
        return AccountService(session).set_employee_password(employee_id, data.password)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден") from exc
    except AccountConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
