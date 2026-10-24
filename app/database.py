import sqlite3
import os
from flask import g, current_app

def get_db():
    """Connect to SQLite database and configure connection."""
    if 'db' not in g:
        db_path = current_app.config['DATABASE_PATH']
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        # Enable SQLite Foreign Keys
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app=None):
    """Initialize the database from schema.sql."""
    if app:
        db_path = app.config['DATABASE_PATH']
        schema_path = app.config['SCHEMA_PATH']
    else:
        db_path = current_app.config['DATABASE_PATH']
        schema_path = current_app.config['SCHEMA_PATH']

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def query_db(query, args=(), one=False):
    """Run a parameterized SELECT query and return dict-like rows."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def query_one(query, args=()):
    """Run a parameterized SELECT query and return exactly one row or None."""
    return query_db(query, args, one=True)

def execute_db(query, args=()):
    """Execute an INSERT, UPDATE, or DELETE query and commit."""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    affected = cur.rowcount
    cur.close()
    return affected

def insert_db(query, args=()):
    """Execute an INSERT query and return the last inserted row id."""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id
