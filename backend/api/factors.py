"""
Emission Factor endpoints.

GET    /factors                          — list factors (filterable)
GET    /factors/{id}                     — get single factor
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from backend.db.database import get_db
from backend.models import EmissionFactor
from backend.schemas.emission import EmissionFactorResponse
from backend.core.calculations.factor_selector import list_available_factors

router = APIRouter()


@router.get("", response_model=list[EmissionFactorResponse])
def list_factors(
    activity_type: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return list_available_factors(
        db=db,
        activity_type=activity_type,
        region=region,
    )


@router.get("/{factor_id}", response_model=EmissionFactorResponse)
def get_factor(factor_id: UUID, db: Session = Depends(get_db)):
    factor = db.query(EmissionFactor).filter_by(id=factor_id).first()
    if not factor:
        raise HTTPException(
            status_code=404, detail="Emission factor not found"
        )
    return factor