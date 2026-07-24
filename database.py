import sqlite3
import csv
import os
from datetime import datetime
from werkzeug.security import generate_password_hash
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_pending_days(reported_date_str, repaired_date_str=None, status='Pending'):
    """
    Calculates derived pending days figure strictly on the server:
    - If status is Repaired and repaired_date is present: elapsed days between reported_date and repaired_date.
    - If pending or in progress: elapsed days between reported_date and today's date.
    - Handles invalid or missing dates gracefully by returning 0.
    """
    if not reported_date_str:
        return 0
    
    try:
        rep_date = datetime.strptime(str(reported_date_str).strip(), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return 0
    
    if status == 'Repaired' and repaired_date_str and str(repaired_date_str).strip():
        try:
            fix_date = datetime.strptime(str(repaired_date_str).strip(), '%Y-%m-%d').date()
            diff = (fix_date - rep_date).days
            return max(0, diff)
        except (ValueError, TypeError):
            pass
            
    # Default to current date for pending/in progress complaints
    today = datetime.now().date()
    diff = (today - rep_date).days
    return max(0, diff)

def init_db():
    """Creates tables and seeds default user and initial complaints dataset if empty."""
    os.makedirs(os.path.dirname(Config.DATABASE), exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Execute SQL schema
    if os.path.exists(Config.SCHEMA_FILE):
        with open(Config.SCHEMA_FILE, 'r', encoding='utf-8') as f:
            cursor.executescript(f.read())
            
    # Check if default admin user exists
    cursor.execute("SELECT id FROM users WHERE username = ?", ('admin',))
    if not cursor.fetchone():
        hashed = generate_password_hash('admin123')
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ('admin', hashed, 'Administrator')
        )
        
    # Check if complaints table is empty, seed from dataset.csv
    cursor.execute("SELECT COUNT(*) FROM complaints")
    count = cursor.fetchone()[0]
    
    if count == 0 and os.path.exists(Config.DATASET_FILE):
        with open(Config.DATASET_FILE, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                fault_id = row.get('fault_id', '').strip()
                pole_id = row.get('pole_id', '').strip()
                ward = row.get('ward', '').strip()
                street = row.get('street', '').strip()
                reported_date = row.get('reported_date', '').strip()
                fault_type = row.get('fault_type', '').strip()
                status = row.get('status', '').strip() or 'Pending'
                repaired_date = row.get('repaired_date', '').strip() or None
                try:
                    need_attention = int(row.get('need_attention', 0))
                except ValueError:
                    need_attention = 0
                
                # Determine priority based on fault type & status
                if fault_type in ['Transformer Failure', 'Pole Structural Damage']:
                    priority = 'Critical'
                elif fault_type in ['Wiring Damage', 'Power Surge']:
                    priority = 'High'
                else:
                    priority = 'Medium'
                
                cursor.execute("""
                    INSERT INTO complaints (
                        fault_id, pole_id, ward, street, reported_date,
                        fault_type, status, repaired_date, need_attention, priority
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fault_id, pole_id, ward, street, reported_date,
                    fault_type, status, repaired_date, need_attention, priority
                ))
    
    conn.commit()
    conn.close()
