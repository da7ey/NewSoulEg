#!/usr/bin/env python3
"""Single-source sync for the exhibitions subsystem of newsouladv.com.

Source of truth: data/exhibitions.json
Generates / checks:
  - exhibitions-egypt.ics                 (full file)
  - exhibitions-calendar.html             (month labels + event cards + month chips + ItemList + counters)
  - exhibitions-guide-egypt.html          (sector-item date text + counters)  [dates: check/apply]
  - index.html                            (top-5 countdown cards)
  - llms.txt                              (full exhibitions list)
  - search-index.js                       (title/description refresh from the real pages)
  - pages themselves                      (countdown block + schema dates vs JSON)  [check only]

Usage (run from the repo root):
  python3 tools/sync_exhibitions.py --check [--today YYYY-MM-DD]
  python3 tools/sync_exhibitions.py --apply [--today YYYY-MM-DD]

To add/change an exhibition: edit data/exhibitions.json (and the exhibition's own page),
run --apply, then deliver the files listed by --apply.
"""
import re, json, sys, datetime, html, os, argparse

AR = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']
EN = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
SITE = 'https://newsouladv.com/'
TBD = 'موعد الدورة القادمة لسه ما اتعلنش'

def rd(f): return open(f, encoding='utf-8', newline='').read()
def wr(f, s): open(f, 'w', encoding='utf-8', newline='').write(s)
def d(s): return datetime.date.fromisoformat(s)
def js(s): return s.replace('\\', '\\\\').replace("'", "\\'")
def startar(s): x = d(s); return f'{x.day} {AR[x.month-1]} {x.year}'

def load():
    data = json.load(open('data/exhibitions.json', encoding='utf-8'))
    conf = sorted([e for e in data if e['status'] == 'confirmed'], key=lambda e: (e['start'], e['name']))
    tbd = [e for e in data if e['status'] != 'confirmed']
    return data, conf, tbd

# ---------------- ICS ----------------
def fold(line):
    out = []; cur = ''
    for ch in line:
        if len((cur + ch).encode()) > 72: out.append(cur); cur = ' ' + ch
        else: cur += ch
    out.append(cur); return '\n'.join(out)

def gen_ics(old, conf):
    head = old[:old.index('BEGIN:VEVENT')]
    ev = []
    for e in conf:
        url = SITE + e['page']
        end = (d(e['end']) + datetime.timedelta(days=1)).strftime('%Y%m%d')
        L = ['BEGIN:VEVENT', f"UID:{e['ics_uid']}@newsouladv.com", 'DTSTAMP:20260911T141404Z',
             'DTSTART;VALUE=DATE:' + e['start'].replace('-', ''), 'DTEND;VALUE=DATE:' + end,
             'SUMMARY:' + e['ics_summary'], 'LOCATION:' + e['ics_location'],
             f'DESCRIPTION:دليل المعارض: {SITE}exhibitions-guide-egypt.html — صفحة المعرض: {url}', 'URL:' + url, 'END:VEVENT']
        ev.append('\n'.join(fold(x) for x in L) + '\n')
    return head + ''.join(ev) + 'END:VCALENDAR'

# ---------------- calendar ----------------
def gen_calendar(c, conf, counts):
    a = c.index('  <div class="calendar-month-label" id="month-oct-2026">') if 'month-oct-2026' in c else None
    m0 = re.search(r'  <div class="calendar-month-label" id="month-(?!tbd)[a-z]+-\d{4}">', c)
    a = m0.start()
    b = c.index('  <p style="max-width:700px;margin:16px auto 0')
    region = c[a:b]
    svg_g = re.search(r'<button type="button" class="calendar-ics-btn" onclick="addToGoogleCalendar[^>]*>(<svg.*?</svg>) Google Calendar</button>', region, re.S).group(1)
    svg_i = re.search(r'<button type="button" class="calendar-ics-btn" onclick="addToCalendar[^>]*>(<svg.*?</svg>) تحميل ملف \(\.ics\)</button>', region, re.S).group(1)
    out = []; cur = None; labels = []
    for e in conf:
        s = d(e['start']); key = (s.year, s.month)
        if key != cur:
            cur = key; lid = f'month-{EN[s.month-1]}-{s.year}'; labels.append((key, lid))
            out.append(f'  <div class="calendar-month-label" id="{lid}">{AR[s.month-1]} {s.year}</div>\n')
        gs = s.strftime('%Y%m%d'); ge = (d(e['end']) + datetime.timedelta(days=1)).strftime('%Y%m%d')
        t = js(e['gcal_title']); v = js(e['gcal_venue'])
        p = ' · '.join([e['date_text'], e['venue'], e['blurb']])
        out.append(f'''  <div class="calendar-item">
    <a href="{SITE}{e['page']}" class="calendar-link">
      <div class="calendar-date"><span class="calendar-day">{s.day}</span><span class="calendar-mon">{AR[s.month-1]}</span></div>
      <div class="calendar-info"><h3>{e['cal_title']}</h3><p>{p}</p></div>
      <span class="calendar-arrow">←</span>
    </a>
    <div class="calendar-btn-row"><button type="button" class="calendar-ics-btn" onclick="addToGoogleCalendar('{gs}','{ge}','{t}','{v}')">{svg_g} Google Calendar</button><button type="button" class="calendar-ics-btn" onclick="addToCalendar('{gs}','{ge}','{t}','{v}')">{svg_i} تحميل ملف (.ics)</button></div>
  </div>

''')
    c = c[:a] + ''.join(out) + c[b:]
    first = {}
    for (y, mo), lid in labels: first.setdefault(mo, lid)
    toc = ''.join(f'<li><a href="#{first.get(mo+1, "month-tbd")}">{AR[mo]}</a></li>' for mo in range(12))
    c, n = re.subn(r'(<ul class="toc-list" id="tocList">).*?(<li><a href="#faq">)', lambda mm: mm.group(1) + toc + mm.group(2), c, flags=re.S); assert n == 1
    c = set_itemlist(c, [SITE + e['page'] for e in conf], 'exhibitions-calendar')
    return counts_calendar(c, counts)

def set_itemlist(c, urls, marker):
    done = False
    def fix(m):
        nonlocal done
        j = m.group(1)
        try: dd = json.loads(j)
        except Exception: return m.group(0)
        if dd.get('@type') != 'ItemList': return m.group(0)
        dd['itemListElement'] = [{"@type": "ListItem", "position": i + 1, "url": u} for i, u in enumerate(urls)]
        done = True
        return '<script type="application/ld+json">' + json.dumps(dd, ensure_ascii=False, separators=(',', ':')) + '</script>'
    c = re.sub(r'<script type="application/ld\+json">(.*?)</script>', fix, c, flags=re.S)
    assert done, 'no ItemList in ' + marker
    return c

def counts_calendar(c, k):
    T, N, M = k['total'], k['conf'], k['tbd']
    c = re.sub(r'(— |الكامل - |الكامل - )\d+( معرضًا مرتبين)', lambda m: f'{m.group(1)}{N}{m.group(2)}', c)
    c = re.sub(r'(الشاملة بـ <strong>)\d+( معرضًا</strong>)', lambda m: f'{m.group(1)}{N}{m.group(2)}', c)
    c = re.sub(r'(في دليلنا الشامل <strong>)\d+( معرضًا</strong> - منهم <strong>)\d+( معرض بتاريخ مؤكد</strong>.*?<strong>)\d+( معرض لسه)',
               lambda m: f'{m.group(1)}{T}{m.group(2)}{N}{m.group(3)}{M}{m.group(4)}', c, flags=re.S)
    return c

# ---------------- guide ----------------
def gen_guide(g, data, conf, counts):
    T, N, M = counts['total'], counts['conf'], counts['tbd']
    g = re.sub(r'\d+( معرض ومؤتمر)', lambda m: f'{T}{m.group(1)}', g)
    g = re.sub(r'(أكثر من )\d+( معرضًا ومؤتمرًا)', lambda m: f'{m.group(1)}{T}{m.group(2)}', g)
    g = re.sub(r'(من ضمن الـ)\d+( معرض في الدليل، <strong>)\d+( معرض تأكّد ميعادهم رسميًا</strong>)(.*?<strong>)\d+( معرض لسه بانتظار)',
               lambda m: f'{m.group(1)}{T}{m.group(2)}{N}{m.group(3)}{m.group(4)}{M}{m.group(5)}', g, flags=re.S)
    byurl = {SITE + e['page']: e for e in data}
    def fix(m):
        pre, u, mid, txt, post = m.groups()
        e = byurl.get(u)
        if not e: return m.group(0)
        if e['status'] != 'confirmed':
            new = TBD
        else:
            # panels show either the start date or the full range: only rewrite when start day/month/year disagree
            s = d(e['start']); first = re.match(r'(\d+)', txt)
            ok = bool(first) and int(first.group(1)) == s.day and AR[s.month-1] in txt and str(s.year) in txt
            new = txt if ok else startar(e['start'])
        return pre + u + mid + new + post
    g = re.sub(r'(<a href=")(https://newsouladv\.com/[^"]+)(" class="sector-item"[^>]*><div class="sector-item-date">)([^<]*)(</div>)', fix, g)
    return g

# ---------------- homepage ----------------
def gen_home(c, conf, today):
    up = [e for e in conf if e['end'] >= today][:5]
    cards = ''
    for e in up:
        title = html.unescape(e['cal_title']).replace('&', '&') if False else e['cal_title']
        sub = f"{e['date_text']} · {e['venue']}"
        cards += f'<a href="{SITE}{e["page"]}" class="countdown-card"><span class="countdown-days" data-date="{e["start"]}" data-end-date="{e["end"]}">-- يوم</span><h3>{title}</h3><p>{sub}</p></a>\n'
    pat = re.compile(r'(?:<a href="https://newsouladv\.com/[^"]+" class="countdown-card"><span class="countdown-days"[^>]*>[^<]*</span><h3>.*?</h3><p>.*?</p></a>\n){5}', re.S)
    assert pat.search(c), 'homepage cards block not found'
    return pat.sub(lambda m: cards, c, count=1)

# ---------------- llms ----------------
def gen_llms(t, data, conf, tbd):
    L = [f"- [{e['name']}]({SITE}{e['page']}): {startar(e['start'])}" for e in conf]
    L += [f"- [{e['name']}]({SITE}{e['page']}): {TBD}" for e in tbd]
    a = t.index('### القائمة الكاملة'); b = t.index('## مقالات ومصادر')
    return t[:a] + f'### القائمة الكاملة ({len(L)} معرض ومؤتمر، مرتبة زمنيًا)\n\n' + '\n'.join(L) + '\n\n' + t[b:]

# ---------------- search index ----------------
def gen_search(c):
    lines = re.findall(r'^\{.*?\},?$', c, re.M)
    data = [json.loads(l.rstrip(',')) for l in lines]
    for x in data:
        f = x['u'].replace(SITE, '')
        if not f or not os.path.exists(f): continue
        h = rd(f)
        t = re.search(r'<title>(.*?)</title>', h, re.S); m = re.search(r'<meta name="description" content="(.*?)"', h, re.S)
        if t and html.unescape(t.group(1)).strip() != html.unescape(x['t']).strip(): x['t'] = t.group(1).strip()
        if m and html.unescape(m.group(1)).strip() != html.unescape(x['d']).strip(): x['d'] = m.group(1).strip()
    head = c[:c.index('var siteSearchIndex')]
    return head + 'var siteSearchIndex = [\n' + ',\n'.join(json.dumps(x, ensure_ascii=False, separators=(',', ':')) for x in data) + '\n];\n'

# ---------------- page validation ----------------
def validate_pages(data):
    problems = []
    for e in data:
        f = e['page']
        if not os.path.exists(f): problems.append(f'{f}: page missing'); continue
        c = rd(f)
        cd = re.search(r'class="countdown-days" data-date="([^"]+)" data-end-date="([^"]+)"', c)
        ev = None
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', c, re.S):
            try: j = json.loads(m.group(1))
            except Exception: problems.append(f'{f}: invalid JSON-LD'); continue
            if 'Event' in str(j.get('@type')): ev = j
        st = (ev or {}).get('eventStatus', '').split('/')[-1]
        if e['status'] == 'confirmed':
            if not cd: problems.append(f'{f}: confirmed but no countdown block')
            elif cd.groups() != (e['start'], e['end']): problems.append(f'{f}: countdown {cd.groups()} != json')
            if not ev: problems.append(f'{f}: no Event schema')
            else:
                if (ev.get('startDate'), ev.get('endDate')) != (e['start'], e['end']): problems.append(f'{f}: schema dates {ev.get("startDate")}..{ev.get("endDate")} != json')
                if st != 'EventScheduled': problems.append(f'{f}: status {st}')
        else:
            if cd: problems.append(f'{f}: TBD in json but page has countdown')
            if ev and st != 'EventCompleted': problems.append(f'{f}: TBD but schema status {st}')
    return problems

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--apply', action='store_true'); ap.add_argument('--check', action='store_true'); ap.add_argument('--today')
    a = ap.parse_args()
    today = a.today or datetime.date.today().isoformat()
    data, conf, tbd = load()
    counts = dict(total=len(data), conf=len(conf), tbd=len(tbd))
    jobs = {
        'exhibitions-egypt.ics': lambda c: gen_ics(c, conf),
        'exhibitions-calendar.html': lambda c: gen_calendar(c, conf, counts),
        'exhibitions-guide-egypt.html': lambda c: gen_guide(c, data, conf, counts),
        'index.html': lambda c: gen_home(c, conf, today),
        'llms.txt': lambda c: gen_llms(c, data, conf, tbd),
        'search-index.js': gen_search,
    }
    changed = []
    for f, fn in jobs.items():
        old = rd(f); new = fn(old)
        if new != old:
            changed.append(f)
            if a.apply: wr(f, new)
    # search index depends on pages edited by earlier jobs -> rerun after apply
    if a.apply:
        old = rd('search-index.js'); new = gen_search(old)
        if new != old: wr('search-index.js', new); changed.append('search-index.js') if 'search-index.js' not in changed else None
    probs = validate_pages(data)
    print(f'exhibitions: {counts["total"]} (confirmed {counts["conf"]}, tbd {counts["tbd"]}), today={today}')
    print('files', 'written:' if a.apply else 'out of sync:', changed or 'none')
    for p in probs: print('PROBLEM', p)
    if not a.apply and (changed or probs): sys.exit(1)
    if probs: sys.exit(1)

if __name__ == '__main__': main()
