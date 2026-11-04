import os
import sqlite3
from flask import current_app, g
from sqlalchemy.orm import declarative_base

Base = declarative_base()

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('ADMIN','USER','PACIENTE','MEDICO')),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS citas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
  especialidad TEXT NOT NULL,
  fecha_hora TEXT NOT NULL,
  motivo TEXT NOT NULL,
  estado TEXT NOT NULL DEFAULT 'ACTIVA' CHECK (estado IN ('ACTIVA','CANCELADA','PENDIENTE','CONFIRMADA','EN_CONSULTA','COMPLETADA'))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_cita_slot
  ON citas (especialidad, fecha_hora) WHERE estado = 'ACTIVA';
"""


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE"])
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    try:
        get_db().executescript(SCHEMA)
    except Exception:
        pass


db = None