#!/usr/bin/env python
import os
import sys


def main():
    # Force deploy settings on Render (same logic as wsgi.py)
    if os.environ.get('RENDER'):
        os.environ['DJANGO_SETTINGS_MODULE'] = 'eraya.settings.deploy'
    else:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eraya.settings.development')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Activate your virtual environment and run: pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
