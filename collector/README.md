Collector service — README

This document explains how to set up and initialize the database used by the collector service.

Prerequisites
- Docker & docker-compose (recommended) or a local PostgreSQL server
- Python 3.10+ (if running locally)

Option A — Quick start with Docker Compose (recommended)
1. From the repository root, start services (Postgres + collector):

```bash
docker-compose up -d
```

2. Verify Postgres is ready and the `observer` database exists:

```bash
docker-compose exec postgres pg_isready
docker-compose exec postgres psql -U observer -d observer -c "\dt"
```

3. View collector logs (optional):

```bash
docker-compose logs -f collector
```

Notes:
- `init.sql` in the repo root is mounted into the Postgres container and will run on first container startup to create the database and tables.
- If you rebuild the `collector` image or change code, use `docker-compose up --build -d collector` to restart the collector service.

Option B — Local Python + Postgres (no Docker)
1. Ensure PostgreSQL is running locally and create a user & database (example):

```bash
# run as postgres user or via psql
psql -U postgres -c "CREATE USER observer WITH PASSWORD 'password';"
psql -U postgres -c "CREATE DATABASE observer OWNER observer;"
```

2. Set up a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r collector/requirements.txt
```

3. Set the `DATABASE_URL` environment variable and initialize the DB tables using the provided script:

```bash
export DATABASE_URL=postgresql://observer:password@localhost:5432/observer
cd collector
python init_db.py
```

4. Verify tables exist:

```bash
psql "$DATABASE_URL" -c "\dt"
psql "$DATABASE_URL" -c "SELECT count(*) FROM metrics;"
```

Troubleshooting
- The `init_db.py` script will raise "DATABASE_URL environment variable required" if `DATABASE_URL` is not set.
- If `psycopg2` fails to install, install system headers (Debian/Ubuntu):

```bash
sudo apt-get update && sudo apt-get install -y build-essential libpq-dev python3-dev
```

- If using Docker Compose, check `docker-compose logs postgres` for DB init errors.
- If tables are missing after startup, ensure `init.sql` exists in the repo root (it is included) or run `python init_db.py` with the correct `DATABASE_URL`.

Where files live
- Docker Compose: `docker-compose.yml` (repo root)
- DB init SQL: `init.sql` (repo root)
- Collector DB init script: `collector/init_db.py`

If you want, I can:
- Run the Docker Compose setup here and verify the collector connected to the DB, or
- Add these steps to the repo root `README.md` as well.
