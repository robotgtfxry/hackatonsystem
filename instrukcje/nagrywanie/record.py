"""Nagrywa filmy instruktażowe hackathonsystem przy użyciu Playwright.

Użycie: python record.py <base_url> <out_dir> [lider|admin|juror ...]
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip('/')
OUT = Path(sys.argv[2])
WHICH = sys.argv[3:] or ['lider', 'admin', 'juror']
TMP = Path(__file__).parent / 'raw'
TTS_DIR = Path(__file__).parent / 'tts_cache'
W, H = 1280, 720
FF = imageio_ffmpeg.get_ffmpeg_exe()
# Lektor: neuronowy głos Microsoft (pakiet edge-tts). Alternatywa: pl-PL-ZofiaNeural
VOICE = os.environ.get('TTS_VOICE', 'pl-PL-MarekNeural')
RATE = os.environ.get('TTS_RATE', '+0%')
DEBUG = os.environ.get('REC_DEBUG') == '1'

OVERLAY_JS = r"""
(() => {
  const ss = {
    get(k) { try { return sessionStorage.getItem(k); } catch (e) { return window['__' + k]; } },
    set(k, v) { try { sessionStorage.setItem(k, v); } catch (e) { window['__' + k] = v; } },
  };
  function mk() {
    if (document.getElementById('__cap') || !document.documentElement) return;
    const cap = document.createElement('div');
    cap.id = '__cap';
    Object.assign(cap.style, {
      position: 'fixed', left: '50%', bottom: '26px', transform: 'translateX(-50%)',
      maxWidth: '86%', background: 'rgba(17,22,30,.90)', color: '#fff',
      font: '600 23px/1.4 "Segoe UI", system-ui, sans-serif', padding: '14px 28px',
      borderRadius: '12px', zIndex: 2147483646, textAlign: 'center', pointerEvents: 'none',
      boxShadow: '0 8px 28px rgba(0,0,0,.35)', borderLeft: '6px solid #4caf50',
    });
    const t = ss.get('cap') || '';
    cap.textContent = t; cap.style.display = t ? 'block' : 'none';
    const cur = document.createElement('div');
    cur.id = '__cur';
    const p = JSON.parse(ss.get('pos') || '[640,360]');
    Object.assign(cur.style, {
      position: 'fixed', left: p[0] + 'px', top: p[1] + 'px', width: '22px', height: '22px',
      margin: '-11px 0 0 -11px', borderRadius: '50%', background: 'rgba(255,193,7,.55)',
      border: '2px solid #e0a800', zIndex: 2147483647, pointerEvents: 'none',
      transition: 'transform .15s',
    });
    document.documentElement.append(cap, cur);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mk); else mk();
  window.addEventListener('mousemove', e => {
    const c = document.getElementById('__cur');
    if (c) { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }
    ss.set('pos', JSON.stringify([e.clientX, e.clientY]));
  }, true);
  window.addEventListener('mousedown', () => {
    const c = document.getElementById('__cur');
    if (c) { c.style.transform = 'scale(1.8)'; setTimeout(() => c.style.transform = '', 220); }
  }, true);
  window.__setCap = t => {
    ss.set('cap', t); mk();
    const c = document.getElementById('__cap');
    if (c) { c.textContent = t; c.style.display = t ? 'block' : 'none'; }
  };
})();
"""

TITLE_HTML = """<!doctype html><meta charset="utf-8">
<body style="margin:0;height:100vh;display:flex;flex-direction:column;justify-content:center;
align-items:center;background:linear-gradient(135deg,#1e3d1a,#2d5a27 55%,#3f7a37);color:#fff;
font-family:'Segoe UI',system-ui,sans-serif">
<div style="font-size:22px;letter-spacing:.2em;opacity:.75;text-transform:uppercase">hackathonsystem &middot; instrukcja {num}</div>
<div style="font-size:60px;font-weight:700;margin:18px 0 14px">{title}</div>
<div style="font-size:26px;opacity:.9;max-width:900px;text-align:center;line-height:1.4">{subtitle}</div>
</body>"""


def _spoken(text):
    """Tekst napisu -> tekst dla lektora (bez znaków, które TTS czyta dziwnie)."""
    for a, b in [('„', ''), ('”', ''), (' - ', ', '), (' → ', ', potem '), ('+ ', ''),
                 ('(kapitan)', ', czyli kapitan,'), ('PDF', 'pe-de-ef'), ('QR', 'ku-er')]:
        text = text.replace(a, b)
    return text


def _duration(path):
    out = subprocess.run([FF, '-i', str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r'Duration: (\d+):(\d+):([\d.]+)', out).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def tts(text):
    """Generuje (z cache) nagranie lektora dla tekstu. Zwraca (ścieżka, długość w s)."""
    spoken = _spoken(text)
    path = TTS_DIR / (hashlib.sha1(f'{VOICE}|{RATE}|{spoken}'.encode()).hexdigest()[:16] + '.mp3')
    if not path.exists():
        TTS_DIR.mkdir(exist_ok=True)
        for attempt in range(4):
            try:
                r = subprocess.run([sys.executable, '-m', 'edge_tts', '--voice', VOICE, '--rate', RATE,
                                    '--text', spoken, '--write-media', str(path)],
                                   capture_output=True, timeout=45)
            except subprocess.TimeoutExpired:
                path.unlink(missing_ok=True)
                continue
            if r.returncode == 0 and path.exists() and path.stat().st_size > 1000:
                break
            time.sleep(2 + attempt * 3)
        else:
            raise RuntimeError(f'TTS nie powiódł się: {spoken}\n{r.stderr.decode(errors="replace")}')
    return path, _duration(path)


class Rec:
    def __init__(self, page, t0=None):
        self.p = page
        self.t0 = t0 or time.time()
        self.cues = []  # (sekunda od t0, plik audio)
        self.sync_t = None  # moment pokazania planszy tytułowej (sekunda od t0)

    def _speak(self, text, pad=0.45):
        path, dur = tts(text)  # najpierw generacja, żeby napis i głos startowały razem
        t1 = time.time()
        self.p.evaluate('t => window.__setCap && window.__setCap(t)', text)
        self.cues.append((time.time() - self.t0, path))
        if DEBUG:
            print(f'  [{time.time() - self.t0:6.1f}s] lektor {dur:.1f}s (napis {time.time() - t1:.2f}s): {text[:50]}', flush=True)
        time.sleep(dur + pad)

    def title(self, num, title, subtitle):
        path, dur = tts(f'{title}. {subtitle}.')
        # znacznik synchronizacji: biała klatka -> plansza w znanym momencie
        self.p.set_content('<body style="margin:0;background:#fff"></body>')
        time.sleep(1.0)
        self.p.set_content(TITLE_HTML.format(num=num, title=title, subtitle=subtitle))
        self.sync_t = time.time() - self.t0
        time.sleep(0.8)
        self.cues.append((time.time() - self.t0, path))
        time.sleep(dur + 0.9)

    def go(self, path):
        self.p.goto(BASE + path)
        self.p.wait_for_load_state('networkidle')

    def say(self, text, secs=None):
        """Napis + lektor. Film czeka, aż lektor skończy (secs to tylko minimalny czas)."""
        start = time.time()
        self._speak(text)
        if secs:
            time.sleep(max(0, secs - (time.time() - start)))

    def _move_to(self, loc):
        loc.scroll_into_view_if_needed()
        time.sleep(0.25)
        b = loc.bounding_box()
        self.p.mouse.move(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2, steps=28)
        loc.evaluate("""el => { const o = el.style.outline, s = el.style.outlineOffset;
            el.style.outline = '3px solid #ffc107'; el.style.outlineOffset = '2px';
            setTimeout(() => { el.style.outline = o; el.style.outlineOffset = s; }, 900); }""")
        time.sleep(0.45)

    def click(self, sel, wait_nav=True):
        loc = self.p.locator(sel).first if isinstance(sel, str) else sel
        self._move_to(loc)
        loc.click()
        if wait_nav:
            self.p.wait_for_load_state('networkidle')
        time.sleep(0.6)

    def type(self, sel, text, delay=55):
        loc = self.p.locator(sel).first
        self._move_to(loc)
        loc.click()
        loc.press_sequentially(text, delay=delay)
        time.sleep(0.25)

    def point(self, sel, secs=1.2):
        """Najedź kursorem i podświetl element bez klikania."""
        self._move_to(self.p.locator(sel).first)
        time.sleep(secs)


def new_ctx(browser, record=True):
    kw = dict(viewport={'width': W, 'height': H}, locale='pl-PL', device_scale_factor=1)
    if record:
        kw.update(record_video_dir=str(TMP), record_video_size={'width': W, 'height': H})
    ctx = browser.new_context(**kw)
    ctx.add_init_script(OVERLAY_JS)
    return ctx


def login(r, username, password):
    r.go('/accounts/login/')
    r.type('#id_username', username)
    r.type('#id_password', password, delay=30)
    r.click('form:not([action="/accounts/logout/"]) button[type=submit]')


# ---------------------------------------------------------------- scenariusze

def video_lider(r):
    r.title(1, 'Lider zespołu', 'Rejestracja zespołu, wpisanie członków i oddanie projektu')
    r.go('/')
    r.say('Konto w systemie zakłada tylko lider (kapitan) zespołu. Pozostali członkowie nie potrzebują kont.', 5)
    r.say('Zaczynamy od kliknięcia „Rejestracja”.', 2.2)
    r.click('nav a[href="/accounts/register/"]')
    r.say('Wpisz nazwę swojego zespołu - zespół utworzy się razem z kontem.', 3)
    r.type('#id_team_name', 'Pixel Pirates')
    r.say('Następnie login oraz Twoje imię, nazwisko i email.', 2.2)
    r.type('#id_username', 'anna.nowak')
    r.type('#id_first_name', 'Anna')
    r.type('#id_last_name', 'Nowak')
    r.type('#id_email', 'anna.nowak@example.com', delay=35)
    r.say('Ustaw hasło i powtórz je w drugim polu.', 2)
    r.type('#id_password1', 'Pixel.Pirates.2026', delay=35)
    r.type('#id_password2', 'Pixel.Pirates.2026', delay=35)
    r.say('Kliknij „Zarejestruj się”.', 1.6)
    r.click('form:not([action="/accounts/logout/"]) button[type=submit]')
    r.say('Gotowe! Konto i zespół istnieją, a Ty jesteś kapitanem. Teraz dodaj członków.', 4)
    r.say('Kliknij „+ Dodaj członka”.', 1.8)
    r.click('a:has-text("Dodaj członka")')
    r.say('Wpisz imię i nazwisko członka. Email jest opcjonalny.', 2.6)
    r.type('#id_first_name', 'Tomasz')
    r.type('#id_last_name', 'Wójcik')
    r.type('#id_email', 'tomek.w@example.com', delay=35)
    r.click('form:not([action="/accounts/logout/"]) button[type=submit]')
    r.say('Członek dodany. Tak samo dodajesz kolejne osoby.', 2.6)
    r.click('a:has-text("Dodaj członka")')
    r.type('#id_first_name', 'Julia')
    r.type('#id_last_name', 'Kaczmarek')
    r.click('form:not([action="/accounts/logout/"]) button[type=submit]')
    r.say('Pomyłka w danych? Kliknij „Edytuj” przy osobie i popraw.', 3)
    r.click('.item-row:has-text("Julia") a:has-text("Edytuj")')
    r.type('#id_email', 'julia.k@example.com', delay=35)
    r.click('form:not([action="/accounts/logout/"]) button[type=submit]')
    r.say('Przycisk „Usuń” usuwa członka z zespołu. Limit wielkości zespołu widać przy nagłówku.', 4)
    r.point('.section-header h4', 1.5)
    r.say('Kiedy projekt jest gotowy, kliknij „Oddaj projekt”.', 2.6)
    r.click('a:has-text("Oddaj projekt")')
    r.say('Uzupełnij tytuł, opis, użyte technologie i opcjonalnie linki do repozytorium i demo.', 3.5)
    r.type('#id_title', 'StudyBuddy')
    r.type('#id_description', 'Aplikacja, która dobiera uczniów w pary do wspólnej nauki przed sprawdzianami.', delay=25)
    r.type('#id_technologies', 'Django, HTMX, SQLite', delay=40)
    r.type('#id_repo_url', 'https://github.com/example/studybuddy', delay=25)
    r.click('form:not([action="/accounts/logout/"]) button[type=submit]')
    r.say('Projekt oddany! Do terminu oddania możesz go edytować i dodawać pliki.', 3.5)
    r.point('a:has-text("Edytuj")', 1)
    r.point('a:has-text("Dodaj plik")', 1.2)
    r.say('Swój zespół znajdziesz zawsze na stronie konta - kliknij swoją nazwę w prawym górnym rogu.', 3.5)
    r.click('nav a[href="/accounts/dashboard/"]')
    r.say('To wszystko - powodzenia na hackathonie!', 3)


def video_admin(r, browser):
    r.title(2, 'Administrator', 'Kryteria, jury, sterowanie hackathonem, prezentacje i wyniki')
    r.go('/')
    r.say('Administrator loguje się przez „Zaloguj”.', 2.2)
    login(r, 'admin', 'Admin.Demo.2026')
    r.say('Dashboard admina ma skróty do wszystkich narzędzi.', 3)
    r.say('Najpierw kryteria oceny - kliknij „Kryteria”.', 2.4)
    r.click('a.btn[href="/hackathon/criteria/"]')
    r.say('Każde kryterium ma maksymalną liczbę punktów i wagę w wyniku końcowym.', 3.2)
    r.type('input[name=name]', 'Użyteczność')
    r.type('input[name=description]', 'Czy aplikacja rozwiązuje realny problem', delay=30)
    r.click('form button:has-text("Dodaj")')
    r.say('Kryterium dodane. Teraz członkowie jury.', 2.4)
    r.go('/jury/members/')
    r.say('Lista jurorów. Kliknij „+ Dodaj”.', 2.2)
    r.click('a:has-text("+ Dodaj")')
    r.say('Wpisz jurorów po jednym w linii: imię i nazwisko, przecinek, email.', 3.2)
    r.type('#entries', 'Marek Jankowski, m.jankowski@example.com', delay=35)
    r.click('form button:has-text("Dodaj wszystkich")')
    r.say('Jurorzy nie zakładają kont - łączą się z systemem przez kod QR.', 3)
    r.say('Przebiegiem hackathonu sterujesz w zakładce „Sterowanie”.', 2.6)
    r.click('nav a[href="/jury/status/"]')
    r.say('Status: Planowany → Aktywny (oddawanie projektów) → Ocenianie → Zakończony.', 4)
    r.say('Czas na prezentacje - przełączamy na „Ocenianie”.', 2.4)
    r.click('form:has(input[value=judging]) button')
    r.say('Teraz jurorzy mogą oceniać. Otwórz panel „Prezentacja”.', 2.6)
    r.click('a.btn:has-text("Prezentacja")')
    r.say('Wybierz projekt, który właśnie się prezentuje - jurorzy zobaczą go u siebie.', 3.4)
    r.click('tr:has-text("StudyBuddy") a:has-text("Pokaż")')
    r.say('„Następny” i „Poprzedni” przełączają projekty w trakcie prezentacji.', 3)
    r.point('a:has-text("Poprzedni")', 1)

    # juror otwiera panel w innej przeglądarce (nienagrywane) - potrzebny jego kod
    jctx = new_ctx(browser, record=False)
    jp = jctx.new_page()
    jp.goto(BASE + '/jury/vote/')
    code = jp.locator('code').first.inner_text().strip()

    r.say('Jurorzy otwierają „Link dla jury” na telefonie i widzą kod QR.', 3)
    r.go('/jury/status/')
    r.point('a:has-text("Link dla jury")', 1.2)
    r.say('Ty otwierasz „Skaner QR” i skanujesz kod z ekranu jurora.', 2.8)
    r.click('a.btn:has-text("Skaner QR")')
    r.say('Bez kamery? Wpisz kod ręcznie w polu „Ręczne wprowadzenie”.', 3)
    r.type('#manual-code', code, delay=12)
    r.click('button:has-text("Dalej")', wait_nav=False)
    r.say('Wybierz, który to juror, i kliknij „Sparuj”.', 2.4)
    sel = r.p.locator('#member-select')
    r._move_to(sel)
    sel.select_option(label='Katarzyna Zielińska (k.zielinska@example.com)')
    time.sleep(0.8)
    r.click('button:has-text("Sparuj")', wait_nav=False)
    time.sleep(1.5)
    r.say('Juror sparowany - jego telefon sam przełączy się na panel ocen.', 3.2)
    jctx.close()

    r.say('Wyniki liczą się na bieżąco. Kliknij „Wyniki”.', 2.4)
    r.click('nav a[href="/jury/results/"]')
    r.say('Ranking uwzględnia średnie oceny jury i wagi kryteriów.', 3.4)
    r.p.mouse.wheel(0, 300)
    time.sleep(1.5)
    r.go('/jury/status/')
    r.say('Na dole „Sterowania” pobierzesz PDF: protokół wyników i zestawienie zespołów.', 3.6)
    r.point('a:has-text("Protokół wyników")', 1)
    r.point('a:has-text("Zestawienie zespołów")', 1)
    r.say('Na koniec przełącz status na „Zakończony”. To wszystko!', 3)


def video_juror(r, browser):
    r.title(3, 'Juror', 'Połączenie z panelem jury i ocenianie projektów')
    r.say('Jako juror otwórz link do panelu jury, który dostaniesz od organizatora.', 3.4)
    r.go('/jury/vote/')
    r.say('Na ekranie pojawi się kod QR. Pokaż go administratorowi do zeskanowania.', 3.6)
    r.point('#qrcode', 1.5)
    r.say('Nie musisz niczego klikać - czekaj, aż administrator Cię połączy.', 3)
    code = r.p.locator('code').first.inner_text().strip()

    # administrator paruje jurora (w tle, nienagrywane)
    actx = new_ctx(browser, record=False)
    a = Rec(actx.new_page())
    login(a, 'admin', 'Admin.Demo.2026')
    a.go('/jury/scanner/')
    a.p.fill('#manual-code', code)
    a.p.click('button:has-text("Dalej")')
    a.p.select_option('#member-select', label='Katarzyna Zielińska (k.zielinska@example.com)')
    a.p.click('button:has-text("Sparuj")')
    a.p.wait_for_selector('#scan-result .alert-success', timeout=5000)

    r.p.wait_for_selector('#vote-form', timeout=15000)  # strona sama się odświeża
    r.p.wait_for_load_state('networkidle')
    r.say('Połączono! Widzisz projekt, który właśnie się prezentuje.', 3)
    r.say('Dla każdego kryterium wybierz liczbę punktów.', 2.4)
    for crit, score in [('Innowacyjność', 8), ('Wykonanie techniczne', 9), ('Prezentacja', 7), ('Użyteczność', 10)]:
        btn = r.p.locator(f'#vote-form .card:has-text("{crit}") button.score-btn[data-score="{score}"]').first
        if btn.count():
            r.click(btn, wait_nav=False)
    r.say('Kliknij przycisk zapisu ocen.', 1.8)
    r.click('#submit-btn')
    r.say('Oceny zapisane. Do momentu zmiany projektu możesz je jeszcze poprawić.', 3.4)
    r.say('Gdy administrator przełączy na kolejny projekt, panel odświeży się sam.', 3)
    a.go('/jury/presentation/prev/')
    r.p.wait_for_function('() => !document.body.innerText.includes("StudyBuddy")', timeout=15000)
    r.p.wait_for_load_state('networkidle')
    time.sleep(0.5)
    r.say('Tak jak teraz - nowy projekt, nowe oceny. Powtarzasz to dla każdej prezentacji.', 3.6)
    r.say('To wszystko - dziękujemy za pracę w jury!', 3)
    actx.close()


def _title_frame_time(webm):
    """Pierwsza klatka planszy tytułowej (ciemna) po białej klatce startowej."""
    out = subprocess.run([FF, '-i', str(webm), '-t', '15', '-vf',
                          'signalstats,metadata=print:key=lavfi.signalstats.YAVG', '-an', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    vals = re.findall(r'pts_time:([\d.]+).*?YAVG=([\d.]+)', out, re.S)
    seen_white = False
    for t, y in vals:
        if float(y) > 200:
            seen_white = True
        elif seen_white and float(y) < 150:
            return float(t)
    return None


def to_mp4(webm, mp4, cues, sync_t=None):
    """Webm z Playwright + nagrania lektora (wg znaczników czasu) -> mp4 H.264/AAC."""
    dur = _duration(webm)
    shift = 0.0
    v = _title_frame_time(webm) if sync_t is not None else None
    if v is not None:
        shift = v - sync_t
    print(f'  synchronizacja: plansza w wideo {v}s, w skrypcie {sync_t and round(sync_t, 2)}s -> przesunięcie {shift:+.2f}s')
    cues = [(max(t + shift, 0), p) for t, p in cues]
    cmd = [FF, '-y', '-loglevel', 'error', '-i', str(webm)]
    for _, path in cues:
        cmd += ['-i', str(path)]
    parts = [f'[{i}:a]aresample=48000,adelay={int(t * 1000)}:all=1[a{i}]' for i, (t, _) in enumerate(cues, 1)]
    mix = ''.join(f'[a{i}]' for i in range(1, len(cues) + 1))
    parts.append(f'{mix}amix=inputs={len(cues)}:normalize=0:duration=longest,'
                 'highpass=f=60,acompressor=threshold=-18dB:ratio=2.5:attack=5:release=120,'
                 'loudnorm=I=-16:TP=-1.5:LRA=7,apad[aout]')
    parts.append(f'[0:v]fade=t=in:st=0:d=0.6,fade=t=out:st={max(dur - 1.0, 0):.2f}:d=1.0[vout]')
    cmd += ['-filter_complex', ';'.join(parts), '-map', '[vout]', '-map', '[aout]',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', '-movflags', '+faststart', str(mp4)]
    subprocess.run(cmd, check=True)


NAMES = {'lider': '01-lider-zespolu', 'admin': '02-administrator', 'juror': '03-juror'}

def pregenerate():
    """Generuje z góry wszystkie kwestie lektora, żeby nagrywanie nie czekało na sieć."""
    src = Path(__file__).read_text(encoding='utf-8')
    texts = re.findall(r"r\.say\('([^']*)'", src)
    texts += [f'{t}. {s}.' for t, s in re.findall(r"r\.title\(\d+, '([^']*)', '([^']*)'", src)]
    for i, t in enumerate(texts, 1):
        tts(t)
    print(f'lektor: {len(texts)} kwestii gotowych ({VOICE})')


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    pregenerate()
    shutil.rmtree(TMP, ignore_errors=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for which in WHICH:
            ctx = new_ctx(browser)
            t0 = time.time()  # nagrywanie wideo startuje z utworzeniem strony
            page = ctx.new_page()
            r = Rec(page, t0)
            try:
                if which == 'lider':
                    video_lider(r)
                elif which == 'admin':
                    video_admin(r, browser)
                else:
                    video_juror(r, browser)
                time.sleep(1.6)  # oddech przed wyciemnieniem
                elapsed = time.time() - t0
            except Exception:
                page.screenshot(path=str(OUT / f'{which}-error.png'))
                raise
            finally:
                video = page.video
                ctx.close()
            print(f'{which}: czas nagrania {elapsed:.1f}s, wideo {_duration(video.path()):.1f}s, kwestii lektora: {len(r.cues)}')
            to_mp4(video.path(), OUT / f'{NAMES[which]}.mp4', r.cues, r.sync_t)
            print('nagrano', NAMES[which])
        browser.close()
