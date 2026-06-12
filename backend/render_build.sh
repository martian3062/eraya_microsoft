#!/usr/bin/env bash
set -e

export DJANGO_SETTINGS_MODULE=eraya.settings.deploy

pip install -r requirements-deploy.txt
python manage.py collectstatic --noinput
python manage.py migrate
