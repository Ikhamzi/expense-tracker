# Backend Architecture

This document explains how the backend is organized, why it's organized that way, and
every security/scalability change made when it was restructured. It's written for
someone who is comfortable with Python but hasn't necessarily worked with "Domain-Driven
Design" (DDD) or FastAPI's more advanced features before - if a term might be
unfamiliar, it's explained the first time it's used.

**Nothing about how the API behaves from the outside changed.** Every route path, HTTP
method, request/response JSON shape, status code, and error message is identical to
before. The environment variable names the deployed service already uses
(`DATABASE_URL`, `JWT_SECRET_KEY`, `GOOGLE_CLIENT_ID`, `FRONTEND_ORIGIN`) are unchanged.
The live frontend and the Neon database do not need to know this refactor happened.

---

## 1. What changed, and why

Before this refactor, the backend was five flat files: `main.py` had every route
handler *and* the database queries *and* the request-parsing logic all mixed together in
one function per endpoint. That's fine for a small hobby project, but it doesn't scale
well as a codebase grows - it becomes hard to test one piece (like "does signup reject a
duplicate email?") without spinning up the whole HTTP stack, and it's easy to
accidentally couple things that shouldn't be coupled (e.g. a database query becoming
HTTP-aware).

This refactor splits the code into layers with one clear job each (explained in detail
in section 2), and uses each layer boundary as an opportunity to fix a handful of real
security gaps that existed in the original code (section 3) and add a few things that
make the app easier to operate as it grows (section 4).

### Before

```
backend/
  main.py         - FastAPI app, ALL routes, request parsing, business logic, DB queries
  models.py        - SQLAlchemy tables (User, Expense)
  schemas.py        - Pydantic request/response models
  auth.py          - password hashing, JWT, Google token verification, get_current_user
  database.py       - DB engine/session setup
  requirements.txt
  render.yaml
  runtime.txt
  .env.example
```

### After

```
backend/
  domain/
    errors.py               - DomainError, NotFoundError, ValidationError, ConflictError
    entities.py              - framework-free business rules (e.g. parsing "YYYY-MM")
  application/
    auth_service.py          - signup/login/google-auth use cases
    expense_service.py        - list/create/update/delete/summary use cases
  infrastructure/
    config.py                 - validated Settings (reads env vars once, at startup)
    db/
      base.py                  - engine, SessionLocal, get_db(), pool tuning
      models.py                 - SQLAlchemy tables (unchanged columns/types)
    repositories/
      user_repository.py        - all User queries
      expense_repository.py      - all Expense queries
    security/
      passwords.py               - hash_password / verify_password
      tokens.py                   - create_access_token / decode_access_token
      google.py                    - verify_google_token
  interfaces/
    api/
      deps.py                     - get_current_user FastAPI dependency
      schemas.py                   - Pydantic request/response models (+ max_length)
      error_handlers.py             - domain error -> HTTP response mapping
      rate_limit.py                  - shared slowapi Limiter instance
      routers/
        auth_router.py                - POST /auth/signup, /auth/login, /auth/google
        expenses_router.py             - /expenses routes
  main.py                          - composition root only (~10 lines of actual wiring)
  alembic.ini, alembic/            - database migrations
  requirements.txt, render.yaml, runtime.txt, .env.example   (updated, not moved)
```

`models.py`, `schemas.py`, `auth.py`, and `database.py` no longer exist at the top
level - every line of code that used to live in them now lives in one of the files
above, and nothing imports the old paths anymore.

---

## 2. The DDD layers, explained

"Domain-Driven Design" sounds intimidating, but the core idea used here is simple:
**put code that answers different kinds of questions into different folders**, and make
sure the arrows only point one way (inner layers never import from outer layers).

```
domain            <- innermost: pure business rules, no imports from anything below
   ^
application        <- use cases: "what happens when someone signs up"
   ^
infrastructure      <- how we actually talk to the database, hash passwords, etc.
   ^
interfaces           <- outermost: HTTP - how the outside world talks to us
```

### `domain/` - the business rules themselves

This layer has **no idea FastAPI, SQLAlchemy, or HTTP exist.** It's just plain Python.
That's what makes it easy to test and easy to reason about: a rule like "a month filter
must be a real YYYY-MM date" doesn't need a database or a web server to check.

- **Concrete example**: `domain/entities.py` has `parse_month_range("2026-02")`, which
  turns a month string into a (first day, last day) pair, or raises
  `domain.errors.ValidationError` if it's not a valid month. Both the expense list
  endpoint and the summary endpoint use this - it's a genuine shared business rule, not
  just per-field validation (which Pydantic already handles in `interfaces/api/schemas.py`).
- `domain/errors.py` defines the error *types* (`NotFoundError`, `ValidationError`,
  `ConflictError`) but doesn't know what HTTP status code they map to - that's an
  interface-layer decision (see below).

### `application/` - the use cases

This layer answers "what should happen, in what order" for one user action, e.g.
"someone is signing up." It calls into `infrastructure/` to actually do things
(check the database, hash a password) but doesn't know *how* those things are done.

- **Concrete example**: `application/auth_service.py`'s `signup()` function: look up
  whether the email is already taken (via `user_repository`), and if so raise a
  domain `ConflictError`; otherwise hash the password (via `infrastructure.security
  .passwords`) and create the user (via `user_repository`), then return a signed
  token. It never writes raw SQL or touches `passlib`/`jose` directly.

### `infrastructure/` - how we actually do things

This layer contains everything that talks to the outside world *except* HTTP:
the database connection, the actual SQL queries, password hashing, JWT signing, and
Google token verification. It also holds `config.py`, since "where do our settings come
from" (environment variables) is itself an infrastructure concern.

- **Concrete example**: `infrastructure/repositories/expense_repository.py`'s
  `list_for_user(db, user_id, month_range)` is the only place in the whole codebase
  that writes the SQLAlchemy query `db.query(Expense).filter(Expense.user_id == ...)`.
  If we ever moved to a different database library, only this file (and
  `user_repository.py`) would need to change.

### `interfaces/` - how the outside world talks to us

This is the only layer that knows about FastAPI, HTTP status codes, and JSON. It
translates between "the internet" and the `application/` layer.

- **Concrete example**: `interfaces/api/routers/expenses_router.py`'s
  `delete_expense` route handler takes the path parameter and the logged-in user,
  calls `application.expense_service.delete_expense(...)`, and returns `{"ok": True}`.
  If that service function raises a domain `NotFoundError`,
  `interfaces/api/error_handlers.py` is what turns that into an HTTP 404 with
  `{"detail": "Expense not found"}` - the exact response this API has always returned.

**One pragmatic exception, called out explicitly**: invalid login credentials and
invalid Google tokens raise `fastapi.HTTPException` directly from
`application/auth_service.py`, rather than a domain error. This API has always
returned **401** for those two cases, and 401 isn't one of the codes the domain-error
mapping produces (only 404/400 are - see below), so keeping those two as direct
HTTPException raises was the simplest way to guarantee the exact same status code and
message a real, already-deployed frontend depends on, instead of forcing everything
into a mapping that doesn't fit.

---

## 3. Security changes

Every change below is implemented in code, not just described - see the file
referenced for each one.

### 3.1 CORS wildcard + credentials

**Risk this closes**: The old code did
`allow_origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else ["*"]` combined with
`allow_credentials=True` unconditionally. If `FRONTEND_ORIGIN` were ever left unset (or
set to `"*"`), that combination tells browsers "any website may make authenticated
requests to this API and read the response." In practice, the parts of this API that
need credentials all use a `Bearer` token in an `Authorization` header rather than
cookies, so the practical exposure was limited - but it's still a well-known
misconfiguration (browsers are moving toward blocking it outright), and it's cheap to
close properly.

**Fix** (`main.py`): if `FRONTEND_ORIGIN` is unset or `"*"`, the app now allows all
origins but sets `allow_credentials=False`, and prints a warning. If a specific origin
is set (as it is on the deployed service), behavior is unchanged from before:
that one origin, with credentials allowed.

### 3.2 Missing security headers

**Risk this closes**: without certain response headers, browsers fall back to more
permissive default behavior in a few specific ways: they may try to "sniff" a
response's content type instead of trusting the one we declared (which can be abused to
get a browser to run a JSON response as script), they'll allow this API's responses to
be embedded in an `<iframe>` on another site (used in clickjacking attacks), and they
may forward this site's full URLs to third-party sites via the `Referer` header.

**Fix** (`main.py`, `add_security_headers` middleware): every response now includes
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and
`Referrer-Policy: strict-origin-when-cross-origin`. `Strict-Transport-Security` (which
tells the browser "only ever use HTTPS for this site") is added only when the request
actually arrived over HTTPS - checked via both `request.url.scheme` and the
`X-Forwarded-Proto` header, since Render terminates TLS at its own edge proxy and
forwards plain HTTP internally, so `request.url.scheme` alone would always say `http`.

### 3.3 No rate limiting on auth endpoints

**Risk this closes**: without a limit, `/auth/login` in particular can be hit as fast
as an attacker's network allows, making password-guessing (trying many passwords
against one email) or credential-stuffing (trying many stolen email/password pairs)
much faster and cheaper. `/auth/signup` without a limit is an easy target for
automated spam-account creation.

**Fix** (`interfaces/api/rate_limit.py`, applied in
`interfaces/api/routers/auth_router.py`): using the `slowapi` library, each of
`/auth/signup`, `/auth/login`, and `/auth/google` is limited to **10 requests per
minute per client IP address**. Exceeding it returns a normal `429 Too Many Requests`
JSON response (registered in `main.py` via slowapi's own exception handler) rather than
an unhandled server error. This was verified directly: hitting `/auth/login` 11 times
in a row from a test client returns `429` starting on the 11th request.

### 3.4 No startup validation of configuration

**Risk this closes**: previously, a missing environment variable would only surface
the first time code that needed it actually ran (e.g. `DATABASE_URL` failed with a
`KeyError` deep inside `database.py` the first time a request touched the database;
`JWT_SECRET_KEY` silently fell back to a public, hardcoded default - `dev-secret-change
-me` - with no warning at all, which would let anyone forge login tokens if that
default ever ended up running in production).

**Fix** (`infrastructure/config.py`): a single `pydantic-settings` `Settings` class
reads and validates `DATABASE_URL`, `JWT_SECRET_KEY`, `GOOGLE_CLIENT_ID`,
`FRONTEND_ORIGIN`, and `ENV` once, when the app starts (not lazily on first use), and
every other module imports the resulting `settings` object instead of touching
`os.environ` directly. Two specific checks were added:
- Missing required variables now raise a clear `RuntimeError` naming exactly which
  variable is missing, instead of a confusing error from deep inside unrelated code.
- **If `ENV=production` and `JWT_SECRET_KEY` is still the old default value
  (`dev-secret-change-me`), the app refuses to start at all.** This was verified
  directly (see section 6): with `ENV=production` and the default secret, importing
  the config module raises immediately with a clear message; with a real secret, it
  boots normally.

### 3.5 Request size limits missing from a few text fields

**Risk this closes**: `name`, `category`, and `description` had no maximum length, so
a client could send an arbitrarily large string in any of those fields - wasted
database storage, and a (small) way to send oversized payloads at the API.

**Fix** (`interfaces/api/schemas.py`): added `max_length` constraints - `name` (200),
`category` (100), `description` (1000) - alongside the constraints that already
existed (`password` `min_length=6`, `amount` `gt=0`, all unchanged). None of these
new limits are small enough to reject any realistic legitimate value, so no valid
existing request becomes invalid.

### 3.6 Token claims

Not a vulnerability fix, but a hardening/observability improvement: signed tokens
(`infrastructure/security/tokens.py`) now include `iat` (issued-at time) and `iss`
(issuer, `"expense-tracker-api"`) claims in addition to the existing `sub` (user id)
and `exp` (expiry). These make a token easier to audit (you can tell when it was
issued and confirm it came from this API) without changing what a token grants access
to. Decoding does **not** require these claims to be present, so tokens already issued
to logged-in users before this change keep working normally until they expire (nobody
is logged out by this change).

---

## 4. Scalability hooks

These changes don't fix a specific vulnerability, but make the app easier to operate
and extend as real usage grows:

- **Repository pattern** (`infrastructure/repositories/`): every database query is
  now in exactly one place per table. Adding a new query, changing how pagination
  works, or eventually swapping to a different ORM only touches these two files
  instead of being scattered across route handlers.
- **Rate limiting** (`interfaces/api/rate_limit.py`): beyond the security benefit
  above, this also protects the (currently free-tier, limited) database from being
  overwhelmed by a retry loop or misbehaving client hitting auth endpoints.
- **Connection pool tuning** (`infrastructure/db/base.py`): `pool_size=5`,
  `max_overflow=5`, `pool_pre_ping=True`, `pool_recycle=300`. Render's free web
  service tier and Neon's free tier both have limited concurrent-connection budgets;
  capping the pool keeps this API from opening more connections than it needs.
  `pool_pre_ping` and `pool_recycle` matter specifically because Neon (and many
  managed Postgres providers) will silently close idle connections - without these,
  the next query on a dead connection would fail with a confusing error instead of
  SQLAlchemy transparently reconnecting first.
- **Alembic migrations** (`alembic/`): schema changes are now tracked, one file per
  change, instead of relying on `Base.metadata.create_all()` (which can only *add*
  new tables - it can't rename a column, change a type, or drop something safely).
  As the app grows past two tables, this is the difference between "carefully hand-run
  SQL against production and hope you got it right" and "run one command, and get a
  reviewable, revertible history of every schema change."

---

## 5. Environment variables

**No new required environment variables.** The four that already existed -
`DATABASE_URL`, `JWT_SECRET_KEY`, `GOOGLE_CLIENT_ID`, `FRONTEND_ORIGIN` - are still the
only ones this app needs to run, with the same names, same meanings, same defaults
where they had one. `pydantic-settings`, `slowapi`, and `alembic` (the three new
dependencies) don't need any environment variables of their own.

One **optional** variable was added: `ENV` (defaults to `"development"` if unset).
Setting `ENV=production` turns on the JWT-secret safety check described in 3.4. It has
been added to `render.yaml` for the deployed service; you don't need to set it for
local development.

### `render.yaml` change

The `startCommand` changed from:
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```
to:
```
alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT
```
`main.py` no longer calls `Base.metadata.create_all()` on startup (that approach can't
handle real schema changes going forward - see section 4). From now on, the API server
only starts after any pending migrations have been applied.

**This has one important one-time consequence for the existing production database**,
covered in detail in the next section: the `users` and `expenses` tables already exist
in the live Neon database (created by the old `create_all()` behavior), so the very
first time this new code deploys, `alembic upgrade head` must NOT try to create them
again. You need to run one command by hand, once, before that first deploy.

---

## 6. How to run this locally (and the one-time production step)

### Local development, fresh database

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # on macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

copy .env.example .env       # on macOS/Linux: cp .env.example .env
# then edit .env and fill in DATABASE_URL, JWT_SECRET_KEY, GOOGLE_CLIENT_ID

# Create the schema (users, expenses tables) via Alembic instead of create_all():
alembic upgrade head

uvicorn main:app --reload
```

The API is now running at `http://localhost:8000` - same as before this refactor.
`http://localhost:8000/docs` still has the interactive Swagger UI, and
`http://localhost:8000/` still returns `{"status": "ok"}`.

### The existing production database - one-time step, do this BEFORE the next deploy

The live Neon database already has the `users` and `expenses` tables (created by the
old code's `Base.metadata.create_all()`). If you deploy this refactored code as-is, the
new `startCommand` will run `alembic upgrade head`, which will try to **create** those
tables again and fail, because they already exist.

The fix is to tell Alembic "the database is already at this migration" without running
any SQL, using `stamp` instead of `upgrade`. Do this **once**, before the first deploy
of this refactored code, from a shell that can reach the production `DATABASE_URL`
(e.g. Render's own **Shell** tab on the backend service, or your own machine with
`DATABASE_URL` temporarily set to the production connection string):

```bash
alembic stamp head
```

That's it - it just writes a row into a new `alembic_version` table recording "this
database is at revision 0001," and touches nothing else. After that one-time step,
every future deploy runs `alembic upgrade head` normally (applying only *new*
migrations you add later), exactly like a project that had Alembic from day one.

If you forget this step and `alembic upgrade head` fails on deploy with an error about
`users` (or `expenses`) already existing, that's the symptom - run `alembic stamp head`
against production and redeploy.
