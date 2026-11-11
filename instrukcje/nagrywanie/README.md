# Nagrywanie filmów instruktażowych

Filmy w `instrukcje/` są nagrywane automatycznie (Playwright) na osobnej bazie demo -
prawdziwa `db.sqlite3` nie jest używana. Lektor: neuronowy głos Microsoft `pl-PL-MarekNeural`
(pakiet `edge-tts`, wymaga internetu; do serwera trafiają tylko teksty napisów).
Inny głos: ustaw `TTS_VOICE=pl-PL-ZofiaNeural`, tempo: `TTS_RATE=+10%`.
Teksty lektora = napisy w `record.py` (wywołania `r.say(...)`); nagrania są cache'owane w `tts_cache/`.

Jednorazowo (osobne środowisko z narzędziami do nagrywania):

```
python -m venv instrukcje\nagrywanie\.venv
instrukcje\nagrywanie\.venv\Scripts\pip install playwright imageio-ffmpeg edge-tts
instrukcje\nagrywanie\.venv\Scripts\python -m playwright install chromium
```

Nagranie (PowerShell, z katalogu głównego projektu):

```
$env:PYTHONPATH = "instrukcje\nagrywanie"
Remove-Item instrukcje\nagrywanie\demo.sqlite3 -ErrorAction SilentlyContinue
.venv\Scripts\python manage.py migrate --settings=demo_settings
.venv\Scripts\python manage.py shell --settings=demo_settings -c (Get-Content -Raw instrukcje\nagrywanie\seed.py)
# w osobnym terminalu (z tym samym PYTHONPATH):
.venv\Scripts\python manage.py runserver 127.0.0.1:8001 --settings=demo_settings --noreload
# nagranie wszystkich trzech filmów (kolejność ma znaczenie - każdy korzysta ze stanu po poprzednim):
instrukcje\nagrywanie\.venv\Scripts\python instrukcje\nagrywanie\record.py http://127.0.0.1:8001 instrukcje lider admin juror
```

Przed ponownym nagraniem odtwórz bazę demo (usuń `demo.sqlite3` i powtórz migrate + seed).
