import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.template.loader import get_template
tmpl = get_template('chat/chat_room-FREE.html')
print('Rendering with empty threads...')
try:
    html = tmpl.render({'threads': []})
    print('OK -', len(html), 'bytes')
except Exception as e:
    print('ERROR:', type(e).__name__, e)
