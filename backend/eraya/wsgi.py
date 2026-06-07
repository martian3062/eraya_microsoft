import os
from django.core.wsgi import get_wsgi_application

if os.environ.get('RENDER'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'eraya.settings.deploy'
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eraya.settings.development')

application = get_wsgi_application()
