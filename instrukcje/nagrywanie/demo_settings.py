# Ustawienia tylko do nagrywania filmów - osobna baza demo, prawdziwa baza nietknięta
from pathlib import Path
from hackatonsystem.settings import *  # noqa

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3',
                         'NAME': Path(__file__).resolve().parent / 'demo.sqlite3'}}
MEDIA_ROOT = Path(__file__).resolve().parent / 'media'
