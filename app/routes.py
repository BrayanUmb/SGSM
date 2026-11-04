from datetime import datetime

from flask import Blueprint, current_app, g, jsonify, request

from . import services
from .db import get_db
from .errors import ApiError
from .security import create_token, require_roles
from .validators import pick_allowed

bp = Blueprint("api", __name__, url_prefix="/api")


def _json_body():
    data = request.get_json(silent=True)
    if data is None:
        raise ApiError(400, "JSON body required")
    return data


def _now():
    return current_app.config["CLOCK"]()


@bp.get("/health")
def health():
    return jsonify(status="ok")


@bp.post("/auth/register")
def register():
    data = pick_allowed(_json_body(), ("username", "password"))
    # Role is NEVER taken from the client (API3 mass assignment / API5)
    user = services.create_user(get_db(), data["username"], data["password"], "USER", _now())
    return jsonify(services.public_user(user)), 201


@bp.post("/auth/login")
def login():
    data = pick_allowed(_json_body(), ("username", "password"))
    limiter = current_app.extensions["login_limiter"]
    key = f"{request.remote_addr}:{str(data['username']).lower()}"
    if not limiter.allow(key):
        raise ApiError(429, "Too many failed attempts, try again later")
    try:
        user = services.authenticate(get_db(), data["username"], data["password"])
    except ApiError:
        limiter.fail(key)
        raise
    limiter.reset(key)
    token = create_token(
        user["id"], user["username"], user["role"],
        current_app.config["JWT_SECRET"], current_app.config["JWT_TTL_MINUTES"],
    )
    return jsonify({
        "access_token": token,
        "token_type": "Bearer",  # nosec B105 - HTTP auth scheme name, not a secret
        "expires_in": current_app.config["JWT_TTL_MINUTES"] * 60,
    })


@bp.get("/user/profile")
@require_roles("USER", "ADMIN")
def profile():
    row = get_db().execute("SELECT * FROM usuarios WHERE id = ?", (g.current_user["id"],)).fetchone()
    if row is None:
        raise ApiError(401, "Invalid or expired token")
    return jsonify(services.public_user(row))


@bp.get("/admin/dashboard")
@require_roles("ADMIN")
def admin_dashboard():
    return jsonify(services.dashboard_stats(get_db()))


@bp.get("/admin/citas")
@require_roles("ADMIN")
def admin_citas():
    return jsonify(services.list_all_citas(
        get_db(), request.args.get("page"), request.args.get("size")))


@bp.post("/citas")
@require_roles("USER")
def crear_cita():
    data = pick_allowed(_json_body(), ("especialidad", "fecha_hora", "motivo"))
    row = services.create_cita(
        get_db(), g.current_user["id"], data["especialidad"],
        data["fecha_hora"], data["motivo"], _now())
    return jsonify(services.public_cita(row)), 201


@bp.get("/citas")
@require_roles("USER")
def mis_citas():
    return jsonify(services.list_citas(
        get_db(), g.current_user["id"], request.args.get("page"), request.args.get("size")))


@bp.get("/citas/<int:cita_id>")
@require_roles("USER", "ADMIN")
def ver_cita(cita_id):
    return jsonify(services.public_cita(services.get_cita(get_db(), cita_id, g.current_user)))


@bp.delete("/citas/<int:cita_id>")
@require_roles("USER", "ADMIN")
def cancelar_cita(cita_id):
    return jsonify(services.public_cita(services.cancel_cita(get_db(), cita_id, g.current_user)))
