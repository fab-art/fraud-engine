from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional
import pandas as pd
import io
from datetime import date
from uuid import UUID

from database import get_supabase_client

router = APIRouter()


def validate_file_format(file: UploadFile) -> str:
    """Validate that the file is either CSV or Excel."""
    allowed_extensions = [".csv", ".xlsx", ".xls"]
    filename = file.filename or ""
    
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Allowed formats: {', '.join(allowed_extensions)}"
        )
    
    return filename


def read_file_to_dataframe(file: UploadFile) -> pd.DataFrame:
    """Read uploaded file into a Pandas DataFrame."""
    filename = validate_file_format(file)
    
    try:
        contents = file.file.read()
        
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        elif filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format"
            )
        
        # Reset file pointer for potential re-reading
        file.file.seek(0)
        
        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty"
            )
        
        return df
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )


def clean_dataframe_for_supabase(df: pd.DataFrame) -> list[dict]:
    """Clean DataFrame by converting NaN/NaT values to None or 0 for Supabase compatibility."""
    # Replace NaN and NaT with None
    df_cleaned = df.where(pd.notnull(df), None)
    
    # Convert to list of dictionaries
    records = df_cleaned.to_dict(orient="records")
    
    # Additional cleaning for each record
    cleaned_records = []
    for record in records:
        cleaned_record = {}
        for key, value in record.items():
            # Handle pandas Timestamp objects
            if isinstance(value, pd.Timestamp):
                if pd.isna(value):
                    cleaned_record[key] = None
                else:
                    cleaned_record[key] = value.date() if hasattr(value, 'date') else str(value)
            # Handle pandas NaT
            elif isinstance(value, type(pd.NaT)):
                cleaned_record[key] = None
            # Handle float NaN
            elif isinstance(value, float) and pd.isna(value):
                cleaned_record[key] = None
            # Convert numeric strings that should be numbers
            elif key == "insurance_copay" and value is not None:
                try:
                    cleaned_record[key] = float(value) if value != "" else None
                except (ValueError, TypeError):
                    cleaned_record[key] = None
            else:
                cleaned_record[key] = value
        cleaned_records.append(cleaned_record)
    
    return cleaned_records


@router.post("/api/v1/ingest/pharmacy")
async def ingest_pharmacy_data(
    file: UploadFile = File(...),
    uploaded_by: Optional[str] = Form(None)
):
    """
    Ingest pharmacy claims data from uploaded file.
    
    Creates an audit batch, inserts claims, and updates batch status.
    
    Expected columns: paper_code, patient_rama, patient_name, dispensing_date, 
                     facility_name, prescriber_name, drug_code, insurance_copay
    """
    supabase = get_supabase_client()
    
    # Validate uploaded_by if provided
    if uploaded_by:
        try:
            UUID(uploaded_by)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format for uploaded_by"
            )
    
    try:
        # Create audit batch record
        batch_data = {
            "filename": file.filename or "unknown",
            "uploaded_by": uploaded_by,
            "status": "processing",
            "total_claims": 0
        }
        
        batch_result = supabase.table("audit_batches").insert(batch_data).execute()
        
        if not batch_result.data or len(batch_result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create audit batch"
            )
        
        batch_id = batch_result.data[0]["id"]
        
        # Read and process the uploaded file
        df = read_file_to_dataframe(file)
        
        # Validate required columns
        required_columns = [
            "paper_code", "patient_rama", "patient_name", "dispensing_date",
            "facility_name", "prescriber_name", "drug_code", "insurance_copay"
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            # Clean up the batch if we can't proceed
            supabase.table("audit_batches").delete().eq("id", batch_id).execute()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Select and rename columns as needed
        claims_df = df[required_columns].copy()
        
        # Clean data for Supabase
        claims_records = clean_dataframe_for_supabase(claims_df)
        
        # Add batch_id to each record
        for record in claims_records:
            record["batch_id"] = batch_id
            # Set default verification_status
            record["verification_status"] = "pending"
        
        # Bulk insert claims
        if claims_records:
            claims_result = supabase.table("claims").insert(claims_records).execute()
            
            if not claims_result.data:
                # Rollback: delete the batch
                supabase.table("audit_batches").delete().eq("id", batch_id).execute()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to insert claims data"
                )
            
            inserted_count = len(claims_result.data)
        else:
            inserted_count = 0
        
        # Update audit batch with total count and status
        update_result = supabase.table("audit_batches").update({
            "total_claims": inserted_count,
            "status": "pending_review"
        }).eq("id", batch_id).execute()
        
        if not update_result.data:
            # Log warning but don't fail - the data is already inserted
            pass
        
        return {
            "message": "Pharmacy data ingested successfully",
            "batch_id": batch_id,
            "inserted_row_count": inserted_count,
            "status": "pending_review"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing pharmacy data: {str(e)}"
        )


@router.post("/api/v1/ingest/facility")
async def ingest_facility_data(
    file: UploadFile = File(...),
    batch_id: str = Form(...)
):
    """
    Ingest hospital visits data from uploaded file.
    
    Links visits to an existing pharmacy audit batch.
    
    Expected columns: patient_rama, visit_date, facility_name
    """
    supabase = get_supabase_client()
    
    # Validate batch_id
    try:
        batch_uuid = UUID(batch_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format for batch_id"
        )
    
    try:
        # Verify the batch exists
        batch_check = supabase.table("audit_batches").select("id").eq("id", batch_uuid).execute()
        
        if not batch_check.data or len(batch_check.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Audit batch with id {batch_id} not found"
            )
        
        # Read and process the uploaded file
        df = read_file_to_dataframe(file)
        
        # Validate required columns
        required_columns = ["patient_rama", "visit_date", "facility_name"]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Select required columns
        visits_df = df[required_columns].copy()
        
        # Clean data for Supabase
        visits_records = clean_dataframe_for_supabase(visits_df)
        
        # Add source_batch_id to each record
        for record in visits_records:
            record["source_batch_id"] = batch_uuid
        
        # Bulk insert hospital visits
        if visits_records:
            visits_result = supabase.table("hospital_visits").insert(visits_records).execute()
            
            if not visits_result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to insert hospital visits data"
                )
            
            inserted_count = len(visits_result.data)
        else:
            inserted_count = 0
        
        return {
            "message": "Facility data ingested successfully",
            "batch_id": batch_id,
            "inserted_row_count": inserted_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing facility data: {str(e)}"
        )
