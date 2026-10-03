"""
Database initialization and connection helpers.
Centralizes SQLite schema and connection management.

Phase 1 Schema: Normalized data model with numeric/UUID PKs and proper relationships.
Migrates from old flat schema automatically on startup.
"""

import sqlite3
import os
import json
import uuid
import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Support DATABASE_URL from environment or fall back to local path
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/backend.db")

# Parse DATABASE_URL to get the file path
if DATABASE_URL.startswith("sqlite:///"):
    # Remove 'sqlite:///' prefix and handle both relative and absolute paths
    db_file = DATABASE_URL[10:]  # Remove 'sqlite:///'
    if not os.path.isabs(db_file):
        # Relative path - resolve relative to this file's directory
        db_file = str(Path(__file__).parent / db_file)
    DB_PATH = Path(db_file)
else:
    # Fallback to default
    DB_PATH = Path(__file__).parent / "data" / "backend.db"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_conn():
    """Get a new database connection with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize Phase 1 normalized database schema and migrate old data."""
    print(f"[DB] Using database: {DB_PATH}")
    conn = get_conn()
    
    # First, check if we need to migrate old schema
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cursor.fetchall()}
    
    # If we have old tables but not new ones, do migration
    if "students" in existing_tables and "face_profiles" not in existing_tables:
        print("[DB] Old schema detected - migrating...")
        _migrate_old_schema_tables(conn)
        print("[DB] Migration complete")
        conn.close()
        return
    
    # Check if new schema already exists
    if "schools" in existing_tables:
        print("[DB] Phase 1 schema already exists")
        conn.close()
        return
    
    # Create new Phase 1 tables from scratch
    print("[DB] Creating Phase 1 schema...")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            address TEXT,
            timezone TEXT DEFAULT 'Asia/Kolkata',
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            name TEXT,
            registration_number TEXT UNIQUE,
            device_id TEXT UNIQUE,
            capacity INTEGER DEFAULT 50,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(school_id) REFERENCES schools(id)
        );
        
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            direction TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(school_id) REFERENCES schools(id)
        );
        
        CREATE TABLE IF NOT EXISTS stops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            geofence_radius INTEGER DEFAULT 125,
            address TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(school_id) REFERENCES schools(id)
        );
        
        CREATE TABLE IF NOT EXISTS route_stops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id INTEGER NOT NULL,
            stop_id INTEGER NOT NULL,
            sequence INTEGER,
            planned_time TEXT,
            FOREIGN KEY(route_id) REFERENCES routes(id),
            FOREIGN KEY(stop_id) REFERENCES stops(id)
        );
        
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            admission_number TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT,
            date_of_birth TEXT,
            class_name TEXT,
            section TEXT,
            profile_photo TEXT,
            gender TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(school_id) REFERENCES schools(id)
        );
        
        CREATE TABLE IF NOT EXISTS guardians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            relationship TEXT,
            phone TEXT,
            email TEXT,
            is_primary INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        );
        
        CREATE TABLE IF NOT EXISTS transport_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            bus_id INTEGER NOT NULL,
            route_id INTEGER NOT NULL,
            pickup_stop_id INTEGER NOT NULL,
            drop_stop_id INTEGER NOT NULL,
            valid_from TEXT NOT NULL,
            valid_until TEXT,
            morning_enabled INTEGER DEFAULT 1,
            afternoon_enabled INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(bus_id) REFERENCES buses(id),
            FOREIGN KEY(route_id) REFERENCES routes(id),
            FOREIGN KEY(pickup_stop_id) REFERENCES stops(id),
            FOREIGN KEY(drop_stop_id) REFERENCES stops(id)
        );
        
        CREATE TABLE IF NOT EXISTS face_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            encoding_version INTEGER DEFAULT 1,
            encoding_count INTEGER DEFAULT 0,
            quality_score REAL,
            enrolled_at TEXT,
            enrolled_by TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        );
        
        CREATE TABLE IF NOT EXISTS face_encodings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            face_profile_id INTEGER NOT NULL,
            encoding TEXT,
            quality_score REAL,
            source_photo TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(face_profile_id) REFERENCES face_profiles(id)
        );
        
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL,
            device_code TEXT UNIQUE,
            ip_address TEXT,
            last_seen TEXT,
            software_version TEXT,
            status TEXT DEFAULT 'offline',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(bus_id) REFERENCES buses(id)
        );
        
        CREATE TABLE IF NOT EXISTS attendance_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_uuid TEXT UNIQUE NOT NULL,
            student_id INTEGER NOT NULL,
            bus_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            confidence REAL,
            direction TEXT,
            latitude REAL,
            longitude REAL,
            photo_path TEXT,
            source_device TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(bus_id) REFERENCES buses(id)
        );
        
        CREATE TABLE IF NOT EXISTS review_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_uuid TEXT UNIQUE,
            student_id INTEGER,
            bus_id INTEGER NOT NULL,
            case_type TEXT NOT NULL,
            confidence REAL,
            evidence_path TEXT,
            status TEXT DEFAULT 'pending',
            assigned_to TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            resolution TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(bus_id) REFERENCES buses(id)
        );
        
        -- Operational tables (unchanged from old schema)
        
        CREATE TABLE IF NOT EXISTS enrollment_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id TEXT,
            name TEXT,
            bus_id TEXT,
            pickup_stop_id TEXT,
            drop_stop_id TEXT,
            twin_group TEXT,
            photos TEXT,
            status TEXT DEFAULT 'processing',
            encodings TEXT,
            error_msg TEXT,
            created_at TEXT
        );
        
        CREATE TABLE IF NOT EXISTS deletion_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deletion_uuid TEXT UNIQUE NOT NULL,
            child_id TEXT NOT NULL,
            student_name TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            synced_count INTEGER DEFAULT 0
        );
        """
    )
    
    # Create indexes for performance
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_students_school_id ON students(school_id);
        CREATE INDEX IF NOT EXISTS idx_students_admission_number ON students(admission_number);
        CREATE INDEX IF NOT EXISTS idx_attendance_events_student_id ON attendance_events(student_id);
        CREATE INDEX IF NOT EXISTS idx_attendance_events_event_uuid ON attendance_events(event_uuid);
        CREATE INDEX IF NOT EXISTS idx_transport_assignments_student_id ON transport_assignments(student_id);
        CREATE INDEX IF NOT EXISTS idx_transport_assignments_bus_id ON transport_assignments(bus_id);
        CREATE INDEX IF NOT EXISTS idx_face_profiles_student_id ON face_profiles(student_id);
        CREATE INDEX IF NOT EXISTS idx_face_encodings_face_profile_id ON face_encodings(face_profile_id);
        """
    )
    
    conn.commit()
    
    # Initialize with default school
    _initialize_default_school(conn)
    
    conn.close()
    print("[DB] Phase 1 schema initialized successfully")


def _migrate_old_schema_tables(conn):
    """Migrate data from old flat schema to new normalized schema."""
    print("[DB] Starting schema migration...")
    
    # Create new Phase 1 tables first
    conn.executescript(
        """
        CREATE TABLE schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            address TEXT,
            timezone TEXT DEFAULT 'Asia/Kolkata',
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        
        CREATE TABLE buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            name TEXT,
            registration_number TEXT UNIQUE,
            device_id TEXT UNIQUE,
            capacity INTEGER DEFAULT 50,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(school_id) REFERENCES schools(id)
        );
        
        CREATE TABLE routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            direction TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(school_id) REFERENCES schools(id)
        );
        
        CREATE TABLE stops_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            geofence_radius INTEGER DEFAULT 125,
            address TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(school_id) REFERENCES schools(id)
        );
        
        CREATE TABLE route_stops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id INTEGER NOT NULL,
            stop_id INTEGER NOT NULL,
            sequence INTEGER,
            planned_time TEXT,
            FOREIGN KEY(route_id) REFERENCES routes(id),
            FOREIGN KEY(stop_id) REFERENCES stops_new(id)
        );
        
        CREATE TABLE students_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            admission_number TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT,
            date_of_birth TEXT,
            class_name TEXT,
            section TEXT,
            profile_photo TEXT,
            gender TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(school_id) REFERENCES schools(id)
        );
        
        CREATE TABLE guardians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            relationship TEXT,
            phone TEXT,
            email TEXT,
            is_primary INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students_new(id)
        );
        
        CREATE TABLE transport_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            bus_id INTEGER NOT NULL,
            route_id INTEGER NOT NULL,
            pickup_stop_id INTEGER NOT NULL,
            drop_stop_id INTEGER NOT NULL,
            valid_from TEXT NOT NULL,
            valid_until TEXT,
            morning_enabled INTEGER DEFAULT 1,
            afternoon_enabled INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students_new(id),
            FOREIGN KEY(bus_id) REFERENCES buses(id),
            FOREIGN KEY(route_id) REFERENCES routes(id),
            FOREIGN KEY(pickup_stop_id) REFERENCES stops_new(id),
            FOREIGN KEY(drop_stop_id) REFERENCES stops_new(id)
        );
        
        CREATE TABLE face_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            encoding_version INTEGER DEFAULT 1,
            encoding_count INTEGER DEFAULT 0,
            quality_score REAL,
            enrolled_at TEXT,
            enrolled_by TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students_new(id)
        );
        
        CREATE TABLE face_encodings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            face_profile_id INTEGER NOT NULL,
            encoding TEXT,
            quality_score REAL,
            source_photo TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(face_profile_id) REFERENCES face_profiles(id)
        );
        
        CREATE TABLE devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL,
            device_code TEXT UNIQUE,
            ip_address TEXT,
            last_seen TEXT,
            software_version TEXT,
            status TEXT DEFAULT 'offline',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(bus_id) REFERENCES buses(id)
        );
        
        CREATE TABLE attendance_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_uuid TEXT UNIQUE NOT NULL,
            student_id INTEGER NOT NULL,
            bus_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            confidence REAL,
            direction TEXT,
            latitude REAL,
            longitude REAL,
            photo_path TEXT,
            source_device TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students_new(id),
            FOREIGN KEY(bus_id) REFERENCES buses(id)
        );
        
        CREATE TABLE review_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_uuid TEXT UNIQUE,
            student_id INTEGER,
            bus_id INTEGER NOT NULL,
            case_type TEXT NOT NULL,
            confidence REAL,
            evidence_path TEXT,
            status TEXT DEFAULT 'pending',
            assigned_to TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            resolution TEXT,
            FOREIGN KEY(student_id) REFERENCES students_new(id),
            FOREIGN KEY(bus_id) REFERENCES buses(id)
        );
        """
    )
    
    conn.commit()
    
    # Create default school
    now = datetime.datetime.utcnow().isoformat()
    cursor = conn.execute(
        """INSERT INTO schools (name, code, timezone, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("Migrated School", "MIGRATED-001", "Asia/Kolkata", "active", now, now)
    )
    school_id = cursor.lastrowid
    conn.commit()
    
    # Migrate stops
    try:
        old_stops = conn.execute("SELECT * FROM stops").fetchall()
        for old_stop in old_stops:
            try:
                conn.execute(
                    """INSERT INTO stops_new (school_id, code, name, latitude, longitude, geofence_radius, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (school_id, old_stop["stop_id"], old_stop.get("name", "Unknown"), 
                     old_stop.get("latitude"), old_stop.get("longitude"), 
                     old_stop.get("radius_m", 125), "active", now, now)
                )
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        print(f"[DB] Migrated {len(old_stops)} stops")
    except Exception as e:
        print(f"[DB] Stop migration error: {e}")
    
    # Migrate students and encodings
    try:
        old_students = conn.execute("SELECT * FROM students").fetchall()
        migrated = 0
        
        for old_student in old_students:
            try:
                cursor = conn.execute(
                    """INSERT INTO students_new 
                       (school_id, admission_number, first_name, last_name, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (school_id, old_student["child_id"], old_student["name"], "",
                     "active", now, now)
                )
                student_id = cursor.lastrowid
                
                # Create face profile
                encodings_str = old_student.get("encodings", "[]")
                try:
                    encodings = json.loads(encodings_str)
                    encoding_count = len(encodings)
                except:
                    encodings = []
                    encoding_count = 0
                
                cursor = conn.execute(
                    """INSERT INTO face_profiles 
                       (student_id, status, encoding_count, quality_score, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (student_id, "active", encoding_count, 1.0, now)
                )
                face_profile_id = cursor.lastrowid
                
                # Insert encodings
                for encoding in encodings:
                    try:
                        enc_json = json.dumps(encoding)
                    except:
                        enc_json = None
                    
                    conn.execute(
                        """INSERT INTO face_encodings 
                           (face_profile_id, encoding, quality_score, created_at)
                           VALUES (?, ?, ?, ?)""",
                        (face_profile_id, enc_json, 1.0, now)
                    )
                
                migrated += 1
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        print(f"[DB] Migrated {migrated} students with face encodings")
    except Exception as e:
        print(f"[DB] Student migration error: {e}")
    
    # Drop old tables and rename new ones
    try:
        conn.execute("DROP TABLE IF EXISTS stops")
        conn.execute("ALTER TABLE stops_new RENAME TO stops")
        conn.execute("DROP TABLE IF EXISTS students")
        conn.execute("ALTER TABLE students_new RENAME TO students")
        conn.commit()
        print("[DB] Old tables replaced with new schema")
    except Exception as e:
        print(f"[DB] Error finalizing migration: {e}")


def _initialize_default_school(conn):
    """Initialize with a default school for development."""
    try:
        now = datetime.datetime.utcnow().isoformat()
        conn.execute(
            """INSERT INTO schools (name, code, timezone, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("Demo School", "DEMO-001", "Asia/Kolkata", "active", now, now)
        )
        conn.commit()
        print("[DB] Created default school: DEMO-001")
    except sqlite3.IntegrityError:
        # School already exists
        pass


def _migrate_old_schema(conn):
    """Migrate data from old flat schema to new normalized schema."""
    print("[DB] Migrating old schema to Phase 1...")
    
    # Create or get default school
    row = conn.execute("SELECT id FROM schools LIMIT 1").fetchone()
    if row:
        school_id = row["id"]
    else:
        now = datetime.datetime.utcnow().isoformat()
        cursor = conn.execute(
            """INSERT INTO schools (name, code, timezone, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("Migrated School", "MIGRATED-001", "Asia/Kolkata", "active", now, now)
        )
        school_id = cursor.lastrowid
        conn.commit()
    
    # Migrate stops (if old format exists)
    try:
        # Rename old stops table temporarily
        conn.execute("ALTER TABLE stops RENAME TO stops_old")
        
        # Create new stops table with new schema
        conn.execute("""
            CREATE TABLE stops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                geofence_radius INTEGER DEFAULT 125,
                address TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(school_id) REFERENCES schools(id)
            )
        """)
        
        # Migrate data from old schema
        old_stops = conn.execute("SELECT * FROM stops_old").fetchall()
        now = datetime.datetime.utcnow().isoformat()
        
        for old_stop in old_stops:
            try:
                conn.execute(
                    """INSERT INTO stops (school_id, code, name, latitude, longitude, geofence_radius, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (school_id, old_stop["stop_id"], old_stop.get("name", "Unknown"), 
                     old_stop.get("latitude"), old_stop.get("longitude"), 
                     old_stop.get("radius_m", 125), "active", now, now)
                )
            except sqlite3.IntegrityError:
                # Already migrated
                pass
        
        # Drop old table
        conn.execute("DROP TABLE stops_old")
        conn.commit()
        print(f"[DB] Migrated {len(old_stops)} stops")
    except Exception as e:
        print(f"[DB] Stop migration skipped: {e}")
        # Ensure stops table exists in new format
        try:
            conn.execute("DROP TABLE IF EXISTS stops_old")
            conn.commit()
        except:
            pass
    
    # Migrate students and face encodings
    try:
        # Rename old students table temporarily
        conn.execute("ALTER TABLE students RENAME TO students_old")
        
        # Create new students table with new schema
        conn.execute("""
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_id INTEGER NOT NULL,
                admission_number TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT,
                date_of_birth TEXT,
                class_name TEXT,
                section TEXT,
                profile_photo TEXT,
                gender TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(school_id) REFERENCES schools(id)
            )
        """)
        
        old_students = conn.execute("SELECT * FROM students_old").fetchall()
        now = datetime.datetime.utcnow().isoformat()
        migrated = 0
        
        for old_student in old_students:
            try:
                # Insert student with child_id as admission_number
                cursor = conn.execute(
                    """INSERT INTO students 
                       (school_id, admission_number, first_name, last_name, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (school_id, old_student["child_id"], old_student["name"], "",
                     "active", now, now)
                )
                student_id = cursor.lastrowid
                
                # Create face profile
                encodings_str = old_student.get("encodings", "[]")
                try:
                    encodings = json.loads(encodings_str)
                    encoding_count = len(encodings)
                except:
                    encodings = []
                    encoding_count = 0
                
                cursor = conn.execute(
                    """INSERT INTO face_profiles 
                       (student_id, status, encoding_count, quality_score, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (student_id, "active", encoding_count, 1.0, now)
                )
                face_profile_id = cursor.lastrowid
                
                # Insert face encodings
                for i, encoding in enumerate(encodings):
                    try:
                        enc_json = json.dumps(encoding)
                    except:
                        enc_json = None
                    
                    conn.execute(
                        """INSERT INTO face_encodings 
                           (face_profile_id, encoding, quality_score, created_at)
                           VALUES (?, ?, ?, ?)""",
                        (face_profile_id, enc_json, 1.0, now)
                    )
                
                migrated += 1
            except sqlite3.IntegrityError:
                # Already migrated
                pass
        
        # Drop old table
        conn.execute("DROP TABLE students_old")
        conn.commit()
        print(f"[DB] Migrated {migrated} students with face encodings")
    except Exception as e:
        print(f"[DB] Student migration error: {e}")
        # Ensure students table exists in new format
        try:
            conn.execute("DROP TABLE IF EXISTS students_old")
            conn.commit()
        except:
            pass
    
    # Migrate events
    try:
        old_events = conn.execute("SELECT * FROM events LIMIT 1").fetchone()
        if old_events:
            # Events migration is complex - keep old table for now
            print("[DB] Events kept in old format for backward compatibility")
    except:
        pass
    
    print("[DB] Migration complete")
