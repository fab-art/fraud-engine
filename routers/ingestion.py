from fastapi import APIRouter, UploadFile, File, HTTPException, status
import pandas as pd
from io import BytesIO

from database import supabase

router = APIRouter()

PHARMACY_REQUIRED_COLUMNS = {
    "paper_code",
    "patient_rama",
    "patient_name",
    "dispensing_date",
    "facility_name",
    "prescriber_name",
    "drug_code",
    "insurance_copay",
}

FACILITY_REQUIRED_COLUMNS = {
    "patient_rama",
    "visit_date",
    "facility_name",
}


def read_excel_or_csv(file: UploadFile) -> pd.DataFrame:
    """Read an uploaded file (CSV or Excel) into a Pandas DataFrame."""
    content = file.file.read()
    filename = file.filename or ""

    if filename.endswith(".csv"):
        return pd.read_csv(BytesIO(content))
    elif filename.endswith((".xlsx", ".xls")):
        return pd.read_excel(BytesIO(content))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a CSV or Excel file.",
        )


@router.post("/pharmacy")
async def ingest_pharmacy_claims(file: UploadFile = File(...)):
    """
    Ingest pharmacy claims from an uploaded file.
    
    Expected columns: paper_code, patient_rama, patient_name, dispensing_date,
                      facility_name, prescriber_name, drug_code, insurance_copay
    """
    try:
        df = read_excel_or_csv(file)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(e)}",
        )

    # Validate required columns
    missing_columns = PHARMACY_REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(missing_columns)}",
        )

    # Prepare records for insertion
    # Convert date columns to string format for JSON serialization
    records = df.to_dict(orient="records")
    for record in records:
        if "dispensing_date" in record and pd.notna(record["dispensing_date"]):
            record["dispensing_date"] = str(record["dispensing_date"])[:10]
        # Ensure numeric fields are properly handled
        if "insurance_copay" in record and pd.isna(record["insurance_copay"]):
            record["insurance_copay"] = None

    if not records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No records found in the uploaded file.",
        )

    try:
        result = supabase.table("claims").insert(records).execute()
        return {
            "message": f"Successfully ingested {len(records)} pharmacy claims.",
            "count": len(records),
            "data": result.data,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database insertion failed: {str(e)}",
        )


@router.post("/facility")
async def ingest_facility_visits(file: UploadFile = File(...)):
    """
    Ingest hospital/facility visits from an uploaded file.
    
    Expected columns: patient_rama, visit_date, facility_name
    """
    try:
        df = read_excel_or_csv(file)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(e)}",
        )

    # Validate required columns
    missing_columns = FACILITY_REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(missing_columns)}",
        )

    # Prepare records for insertion
    records = df.to_dict(orient="records")
    for record in records:
        if "visit_date" in record and pd.notna(record["visit_date"]):
            record["visit_date"] = str(record["visit_date"])[:10]

    if not records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No records found in the uploaded file.",
        )

    try:
        result = supabase.table("hospital_visits").insert(records).execute()
        return {
            "message": f"Successfully ingested {len(records)} facility visits.",
            "count": len(records),
            "data": result.data,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database insertion failed: {str(e)}",
        )
