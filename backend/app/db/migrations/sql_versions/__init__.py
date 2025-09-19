# This makes the 'versions' directory a Python package.
"""
key_states:
    key_identifier TEXT PRIMARY KEY,
    api_key TEXT NOT NULL,
    cool_down_until REAL,
    request_fail_count INTEGER,
    cool_down_entry_count INTEGER,
    current_cool_down_seconds INTEGER,
    last_usage_time REAL,
    is_in_use INTEGER DEFAULT 0,
    is_cooled_down INTEGER DEFAULT 0

auth_keys:
    api_key TEXT PRIMARY KEY,
    alias TEXT NOT NULL,
    call_count INTEGER DEFAULT 0

request_logs:
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    request_time REAL NOT NULL,
    key_identifier TEXT NOT NULL,
    auth_key_alias TEXT NOT NULL,
    model_name TEXT NOT NULL,
    is_success INTEGER NOT NULL
"""
