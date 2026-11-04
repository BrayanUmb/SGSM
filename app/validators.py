"""Pure input-validation helpers (OWASP API3/API4: schema + size validation)."""
import re
from datetime import datetime, timedelta

from .errors import ApiError

ESPECIALIDADES = frozenset(
    {"MEDICINA_GENERAL", "PEDIATRIA", "CARDIOLOGIA", "DERMATOLOGIA", "ODONTOLOGIA"}
)
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50
MAX_DAYS_AHEAD = 90
OPEN_HOUR = 8
CLOSE_HOUR = 18


def validate_username(value):
    if not isinstance(value, str) or not USERNAME_RE.match(value):
        raise ApiError(400, "Invalid username (3-30 chars: letters, digits, _ . -)")
    return value


def validate_password(value):
    if not isinstance(value, str) or len(value) < 10 or len(value) > 128:
        raise ApiError(400, "Password must have between 10 and 128 characters")
    if not (re.search(r"[a-z]", value) and re.search(r"[A-Z]", value)
            and re.search(r"\d", value)):
        raise ApiError(400, "Password must include upper, lower case and a digit")
    return value


def validate_motivo(value):
    if not isinstance(value, str):
        raise ApiError(400, "Invalid motivo")
    value = value.strip()
    if len(value) < 5 or len(value) > 200:
        raise ApiError(400, "Motivo must have between 5 and 200 characters")
    return value


def validate_especialidad(value):
    if value not in ESPECIALIDADES:
        raise ApiError(400, "Unknown especialidad")
    return value


def validate_fecha_hora(value, now):
    """Return a normalized ISO string for a valid appointment slot."""
    if not isinstance(value, str):
        raise ApiError(400, "Invalid fecha_hora")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        raise ApiError(400, "fecha_hora must be ISO-8601") from None
    dt = dt.replace(tzinfo=None)
    if dt <= now:
        raise ApiError(400, "fecha_hora must be in the future")
    if dt > now + timedelta(days=MAX_DAYS_AHEAD):
        raise ApiError(400, "fecha_hora too far in the future")
    if dt.minute not in (0, 30) or dt.second != 0:
        raise ApiError(400, "Slots start at :00 or :30")
    if dt.hour < OPEN_HOUR or dt.hour >= CLOSE_HOUR:
        raise ApiError(400, "Outside office hours (08:00-18:00)")
    return dt.isoformat(timespec="minutes")


def pick_allowed(data, allowed):
    """Whitelist fields and reject unknown ones (mass-assignment, API3)."""
    if not isinstance(data, dict):
        raise ApiError(400, "JSON object expected")
    extra = set(data) - set(allowed)
    if extra:
        raise ApiError(400, "Unexpected fields: " + ", ".join(sorted(extra)))
    missing = [k for k in allowed if k not in data]
    if missing:
        raise ApiError(400, "Missing fields: " + ", ".join(missing))
    return {k: data[k] for k in allowed}


def clamp_page(page, size):
    """Bound pagination values (API4: unrestricted resource consumption)."""
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = DEFAULT_PAGE_SIZE
    page = max(page, 1)
    size = min(max(size, 1), MAX_PAGE_SIZE)
    return page, size
