#!/usr/bin/env bash
set -e
pip install -r requirements-deploy.txt
python manage.py collectstatic --noinput
python manage.py migrate
