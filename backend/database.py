import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError(
        "Missing required environment variables: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
    )


def get_supabase_client() -> Client:
    """Initialize and return a Supabase client instance."""
    try:
        client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        return client
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Supabase client: {str(e)}")
