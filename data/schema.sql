-- SQL Schema for Municipal Street Light Fault Register & Repair Tracker

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fault_id TEXT UNIQUE NOT NULL,
    pole_id TEXT NOT NULL,
    ward TEXT NOT NULL,
    street TEXT NOT NULL,
    reported_date DATE NOT NULL,
    fault_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending',
    repaired_date DATE,
    need_attention INTEGER DEFAULT 0,
    priority TEXT DEFAULT 'Medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_complaints_ward ON complaints(ward);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_fault_type ON complaints(fault_type);
CREATE INDEX IF NOT EXISTS idx_complaints_pole_id ON complaints(pole_id);
