import psycopg
from app.config import SUPABASE_DB_URL

def get_connection():
    return psycopg.connect(SUPABASE_DB_URL)