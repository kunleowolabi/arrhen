"""
Activity Record endpoints.

POST   /activity/upload/csv              — upload CSV file
GET    /activity                         — list activity records
GET    /activity/{id}                    — get single record
GET    /activity/{id}/lineage            — get lineage for a record
GET    /activity/lineage                 — list all lineage records
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from backend.db.database import get_db
from backend.models import ActivityRecord, DataLineage, Organisation
from backend.schemas.activity import (
    ActivityRecordResponse,
    DataLineageResponse,
    CSVUploadResponse,
)
from backend.core.pipelines.csv_importer import import_csv, CSVImportError
from backend.models.enums import DataStatus, ScopeType

router = APIRouter()


@router.post("/upload/csv", response_model=CSVUploadResponse)
async def upload_csv(
    organisation_id: UUID,
    file: UploadFile = File(...),
    uploaded_by: str = "api_user",
    db: Session = Depends(get_db),
):
    org = db.query(Organisation).filter_by(id=organisation_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")

    try:
        contents = await file.read()
        result = import_csv(
            db=db,
            file=contents,
            organisation_id=organisation_id,
            uploaded_by=uploaded_by,
            filename=file.filename or "upload.csv",
        )
        return result
    except CSVImportError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[ActivityRecordResponse])
def list_activity_records(
    organisation_id: Optional[UUID] = Query(None),
    site_id: Optional[UUID] = Query(None),
    scope: Optional[ScopeType] = Query(None),
    period_year: Optional[int] = Query(None),
    status: Optional[DataStatus] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    from backend.models import Site
    query = db.query(ActivityRecord)

    if organisation_id:
        query = query.join(Site).filter(
            Site.organisation_id == organisation_id
        )
    if site_id:
        query = query.filter(ActivityRecord.site_id == site_id)
    if scope:
        query = query.filter(ActivityRecord.scope == scope)
    if period_year:
        query = query.filter(ActivityRecord.period_year == period_year)
    if status:
        query = query.filter(ActivityRecord.status == status)

    return query.offset(offset).limit(limit).all()


@router.get("/lineage", response_model=list[DataLineageResponse])
def list_lineage(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    return (
        db.query(DataLineage)
        .order_by(DataLineage.uploaded_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{record_id}", response_model=ActivityRecordResponse)
def get_activity_record(record_id: UUID, db: Session = Depends(get_db)):
    record = db.query(ActivityRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.get("/{record_id}/lineage", response_model=DataLineageResponse)
def get_record_lineage(record_id: UUID, db: Session = Depends(get_db)):
    record = db.query(ActivityRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if not record.lineage:
        raise HTTPException(
            status_code=404,
            detail="No lineage found for this record",
        )
    return record.lineage

@router.post("/manual", response_model=ActivityRecordResponse)
def create_manual_record(
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    Creates a single ActivityRecord from a manual form entry.
    Validates required fields and writes directly to the database.
    """
    required = ["site_id", "scope", "ghg_category", "fuel_or_material",
                "quantity", "unit", "period_year"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(missing)}",
        )

    try:
        quantity = float(payload["quantity"])
        if quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="quantity must be greater than zero",
            )
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="quantity must be a valid number",
        )

    scope_2_method = None
    if payload.get("scope_2_method"):
        from backend.models.enums import Scope2Method
        scope_2_method = Scope2Method(payload["scope_2_method"])

    record = ActivityRecord(
        site_id=payload["site_id"],
        scope=ScopeType(payload["scope"]),
        scope_2_method=scope_2_method,
        ghg_category=payload["ghg_category"],
        fuel_or_material=payload["fuel_or_material"],
        quantity=quantity,
        unit=payload["unit"],
        period_year=int(payload["period_year"]),
        period_month=int(payload["period_month"])
            if payload.get("period_month") else None,
        activity_description=payload.get("activity_description"),
        supplier_name=payload.get("supplier_name"),
        supplier_tier=int(payload["supplier_tier"])
            if payload.get("supplier_tier") else None,
        status=DataStatus.validated,
        is_flagged_duplicate=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/import/kobo")
def import_from_kobo(
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    Imports submissions from KoboToolbox forms.
    payload: { organisation_id, form_number (1/2/3 or 'all'), uploaded_by }
    """
    from backend.core.pipelines.kobo_connector import ArrhenKoboConnector
    from uuid import UUID as UUIDType
    import os

    org_id = payload.get("organisation_id")
    form_number = payload.get("form_number", "all")
    uploaded_by = payload.get("uploaded_by", "api_user")

    if not org_id:
        raise HTTPException(status_code=400, detail="organisation_id required")

    api_token = os.getenv("KOBO_API_TOKEN")
    if not api_token:
        raise HTTPException(
            status_code=500,
            detail="KOBO_API_TOKEN not configured on server",
        )

    connector = ArrhenKoboConnector(api_token=api_token)

    try:
        if form_number == "all":
            return connector.import_all_forms(
                db=db,
                organisation_id=UUIDType(org_id),
                uploaded_by=uploaded_by,
            )
        else:
            return connector.import_form(
                db=db,
                form_number=int(form_number),
                organisation_id=UUIDType(org_id),
                uploaded_by=uploaded_by,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
