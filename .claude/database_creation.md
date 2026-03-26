---
name: Local PostgreSQL setup for TripleScore
description: Steps to install and configure local PostgreSQL on WSL2 as a replacement for Supabase-hosted DB
type: project
---

Switched from Supabase-hosted PostgreSQL to local PostgreSQL on WSL2. The code (Django ORM + psycopg2) never used the Supabase SDK — only the connection string changed.

**Why:** User wanted a local DB instead of Supabase cloud hosting.

**How to apply:** Use these steps when setting up the backend on a new machine or after a fresh WSL2 install.

---

## Setup Commands (WSL2 Terminal)

```bash
# Install PostgreSQL
sudo apt update && sudo apt install -y postgresql postgresql-contrib

# Start the service (use service, not systemctl — WSL2 has no systemd by default)
sudo service postgresql start

# Create the database and set postgres user password
sudo -u postgres psql -c "CREATE DATABASE triplescore;"
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"

# Run Django migrations (from backend folder with venv active)
cd /home/shivam/TripleScore/TripleScore-Backend
source ../venv/bin/activate
python manage.py migrate
```

## Active DATABASE_URL (in TripleScore-Backend/.env)

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/triplescore
```

## Start PostgreSQL on every WSL2 session

WSL2 does not persist services across restarts. Run this each time:
```bash
sudo service postgresql start
```

## Verify Setup

```bash
python manage.py dbshell
# Inside psql:
\dt   # should list all 23 tables across 7 Django apps
```
