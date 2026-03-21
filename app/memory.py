from collections import defaultdict

SESSION_STORE = defaultdict(list)

def add_message(session_id: str, role: str, content: str):
    SESSION_STORE[session_id].append({"role": role, "content": content})

def get_history(session_id: str, limit: int = 6):
    return SESSION_STORE[session_id][-limit:]