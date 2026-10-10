# Mini Device Fleet Monitor

A lightweight, robust backend application and dashboard for monitoring a fleet of simulated devices emitting periodic heartbeats.

## Architecture

- **Backend**: Python 3.11+ / Django 5.1 / Django REST Framework
- **App**: Single domain app (`devices/`)
- **Status Evaluation**: Evaluated dynamically at request time (ONLINE if received within 30s)
- **Database**: SQLite with Django ORM

## Prerequisites

- Python 3.11+
- Virtual environment (`venv` or `uv`)

## Quickstart

```bash
# Create venv and install dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start the application server
python manage.py runserver
```
