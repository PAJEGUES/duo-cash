#!/bin/sh
set -e
# Aplica as migrações uma vez, antes de subir os workers.
flask db upgrade
exec gunicorn -c gunicorn.conf.py wsgi:app
