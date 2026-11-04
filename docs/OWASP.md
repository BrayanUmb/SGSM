# OWASP API Security Top 10 (2023) – Implemented Controls

| # | OWASP 2023 category | Control implemented | Evidence (code) | Test |
|---|---|---|---|---|
| 1 | API1 – Broken Object Level Authorization | A user can only read/cancel their own appointments; others get 404 | `services.get_cita` | `test_bola_other_user_cannot_read_or_cancel` |
| 2 | API2 – Broken Authentication | Hashed passwords (scrypt), JWT with `exp/iss/aud`, pinned `HS256`, 5-failure lockout, generic errors, timing equalization | `security.py`, `routes.login` | `test_login_lockout_after_5_failures`, `test_alg_none_rejected` |
| 3 | API3 – Broken Object Property Level Authorization | Field whitelist (mass-assignment blocked); role never read from client; responses never expose `password_hash` | `validators.pick_allowed`, `services.public_*` | `test_register_forces_user_role`, `test_cita_mass_assignment_rejected` |
| 4 | API4 – Unrestricted Resource Consumption | 16 KB body cap, page size capped at 50, login rate limiting | `MAX_CONTENT_LENGTH`, `validators.clamp_page`, `RateLimiter` | `test_oversized_body_rejected`, `test_clamp_page` |
| 5 | API5 – Broken Function Level Authorization | RBAC decorator (`ADMIN`, `USER`); admin routes return 403 to users | `security.require_roles` | `test_admin_endpoint_user_forbidden` |
| 6 | API6 – Unrestricted Access to Sensitive Business Flows | Max 3 active appointments per user; unique active slot per specialty/time | `services.create_cita`, `ux_cita_slot` | `test_active_limit_boundary`, `test_double_booking_conflict_and_release` |
| 7 | API8 – Security Misconfiguration | Security headers (HSTS, CSP, nosniff, X-Frame-Options, no-store), generic JSON errors, secret required from env (≥32 chars) | `create_app` | `test_security_headers`, `test_unexpected_error_is_generic`, `test_app_refuses_weak_or_missing_secret` |
| + | Injection (cross-cutting) | 100 % parameterized SQL + strict input validation | `services.py`, `validators.py` | `test_sql_injection_in_login` |
