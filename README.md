# SGCM – Sistema de Gestión de Citas Médicas (API)

[![CI](https://github.com/REEMPLAZAR_USUARIO/sgcm/actions/workflows/ci.yml/badge.svg)](https://github.com/REEMPLAZAR_USUARIO/sgcm/actions/workflows/ci.yml)
[![CodeQL](https://github.com/REEMPLAZAR_USUARIO/sgcm/actions/workflows/codeql.yml/badge.svg)](https://github.com/REEMPLAZAR_USUARIO/sgcm/actions/workflows/codeql.yml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=REEMPLAZAR_ORG_sgcm&metric=alert_status)](https://sonarcloud.io/dashboard?id=REEMPLAZAR_ORG_sgcm)
[![Mutation score](https://img.shields.io/badge/mutation%20score-89.98%25-brightgreen)](.github/workflows/ci.yml)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=REEMPLAZAR_ORG_sgcm&metric=coverage)](https://sonarcloud.io/dashboard?id=REEMPLAZAR_ORG_sgcm)

API REST en Python (Flask) con autenticación **JWT**, autorización **RBAC** (`ADMIN`, `USER`) y controles de la
**OWASP API Security Top 10 (2023)**. Guía de Laboratorio 7 – Taller de Programación 2026-262.

## Ejecución local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export SGCM_JWT_SECRET="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
export SGCM_ADMIN_PASSWORD='<contraseña-fuerte>'
python manage.py admin            # crea el usuario ADMIN
gunicorn -b 127.0.0.1:8000 wsgi:app
```

## Endpoints

| Método | Ruta | Rol |
|---|---|---|
| POST | `/api/auth/register` | público (siempre crea `USER`) |
| POST | `/api/auth/login` | público (devuelve JWT) |
| GET | `/api/user/profile` | `USER`, `ADMIN` |
| GET | `/api/admin/dashboard` | `ADMIN` |
| GET | `/api/admin/citas` | `ADMIN` |
| POST/GET | `/api/citas` | `USER` |
| GET/DELETE | `/api/citas/<id>` | dueño o `ADMIN` |

## Calidad

```bash
pytest --cov=app --cov-branch          # 93 pruebas, 99 % de cobertura
mutmut run && python scripts/check_mutation_score.py 50   # el build falla si el score < 50 %
bandit -r app
```

Resultado de referencia: **609 mutantes, 548 eliminados → 89,98 %** (meta de la guía: > 60 %).
Controles OWASP documentados en [`docs/OWASP.md`](docs/OWASP.md).

## Nota de despliegue
Gunicorn añade la cabecera `Server`; elimínela en el proxy inverso (nginx: `server_tokens off; more_clear_headers Server;`).
