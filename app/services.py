"""Business rules. All SQL is parameterized (injection prevention)."""
import sqlite3

from .errors import ApiError, utc_now
from .security import hash_password, verify_password
from .validators import (
    clamp_page,
    validate_especialidad,
    validate_fecha_hora,
    validate_motivo,
    validate_password,
    validate_username,
)

MAX_ACTIVE_CITAS = 3  # API6: limit a sensitive business flow


def public_user(row):
    return {"id": row["id"], "username": row["username"], "role": row["role"]}


def public_cita(row):
    return {
        "id": row["id"],
        "usuario_id": row["usuario_id"],
        "especialidad": row["especialidad"],
        "fecha_hora": row["fecha_hora"],
        "motivo": row["motivo"],
        "estado": row["estado"],
    }


def create_user(db, username, password, role="USER", now=None):
    validate_username(username)
    validate_password(password)
    now = now or utc_now()
    try:
        cur = db.execute(
            "INSERT INTO usuarios (username, password_hash, role, created_at)"
            " VALUES (?, ?, ?, ?)",
            (username.lower(), hash_password(password), role, now.isoformat()),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise ApiError(409, "Username already exists") from None
    return db.execute("SELECT * FROM usuarios WHERE id = ?", (cur.lastrowid,)).fetchone()


def authenticate(db, username, password):
    row = None
    if isinstance(username, str):
        row = db.execute(
            "SELECT * FROM usuarios WHERE username = ?", (username.lower(),)
        ).fetchone()
    stored = row["password_hash"] if row else None
    ok = isinstance(password, str) and verify_password(password, stored)
    if not ok:
        raise ApiError(401, "Invalid credentials")
    return row


def create_cita(db, user_id, especialidad, fecha_hora, motivo, now):
    validate_especialidad(especialidad)
    fecha = validate_fecha_hora(fecha_hora, now)
    motivo = validate_motivo(motivo)
    active = db.execute(
        "SELECT COUNT(*) FROM citas WHERE usuario_id = ? AND estado = 'ACTIVA'",
        (user_id,),
    ).fetchone()[0]
    if active >= MAX_ACTIVE_CITAS:
        raise ApiError(429, "Active appointments limit reached")
    try:
        cur = db.execute(
            "INSERT INTO citas (usuario_id, especialidad, fecha_hora, motivo)"
            " VALUES (?, ?, ?, ?)",
            (user_id, especialidad, fecha, motivo),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise ApiError(409, "Slot already taken") from None
    return db.execute("SELECT * FROM citas WHERE id = ?", (cur.lastrowid,)).fetchone()


def list_citas(db, user_id, page, size):
    page, size = clamp_page(page, size)
    rows = db.execute(
        "SELECT * FROM citas WHERE usuario_id = ? ORDER BY fecha_hora LIMIT ? OFFSET ?",
        (user_id, size, (page - 1) * size),
    ).fetchall()
    return {"page": page, "size": size, "items": [public_cita(r) for r in rows]}


def list_all_citas(db, page, size):
    page, size = clamp_page(page, size)
    rows = db.execute(
        "SELECT * FROM citas ORDER BY fecha_hora LIMIT ? OFFSET ?",
        (size, (page - 1) * size),
    ).fetchall()
    return {"page": page, "size": size, "items": [public_cita(r) for r in rows]}


def get_cita(db, cita_id, user):
    """BOLA (API1): only the owner or an ADMIN can read an appointment."""
    row = db.execute("SELECT * FROM citas WHERE id = ?", (cita_id,)).fetchone()
    if row is None or (row["usuario_id"] != user["id"] and user["role"] != "ADMIN"):
        raise ApiError(404, "Appointment not found")
    return row


def cancel_cita(db, cita_id, user):
    row = get_cita(db, cita_id, user)
    if row["estado"] == "CANCELADA":
        raise ApiError(409, "Appointment already cancelled")
    db.execute("UPDATE citas SET estado = 'CANCELADA' WHERE id = ?", (cita_id,))
    db.commit()
    return get_cita(db, cita_id, user)


def dashboard_stats(db):
    total_users = db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    activas = db.execute("SELECT COUNT(*) FROM citas WHERE estado='ACTIVA'").fetchone()[0]
    canceladas = db.execute(
        "SELECT COUNT(*) FROM citas WHERE estado='CANCELADA'"
    ).fetchone()[0]
    return {"usuarios": total_users, "citas_activas": activas, "citas_canceladas": canceladas}
