import sqlite3
import json

DB_FILE = "database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Table 1: User Logins
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            date TEXT NOT NULL
        )
    ''')
    
    # Table 2: Required Transaction Pipeline Fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaction_details (
            acn TEXT,
            cid TEXT PRIMARY KEY,
            aod TEXT,
            dr_cr TEXT,
            txn_amt REAL,
            closing_bal REAL,
            channel TEXT,
            narration TEXT,
            occupation TEXT,
            turnover REAL
        )
    ''')

    # Table 3: JSON Rule Configuration Matrix Registry
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rules_config (
            rule_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            rule_json TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def save_rule_to_db(rule_id, name, rule_payload):
    """Saves or updates a compiled JSON configuration row smoothly."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO rules_config (rule_id, name, rule_json) 
        VALUES (?, ?, ?)
        ON CONFLICT(rule_id) DO UPDATE SET name=excluded.name, rule_json=excluded.rule_json
    ''', (rule_id, name, json.dumps(rule_payload)))
    conn.commit()
    conn.close()