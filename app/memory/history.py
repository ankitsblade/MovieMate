from langgraph.checkpoint.postgres import PostgresSaver
from app.config import SUPABASE_DB_URL

checkpointer_cm = PostgresSaver.from_conn_string(SUPABASE_DB_URL)
checkpointer = checkpointer_cm.__enter__()

# Creates checkpoint tables if they do not exist yet.
checkpointer.setup()