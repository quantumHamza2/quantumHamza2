"""Generate a self-hosted profile panel from public GitHub data, using stdlib only."""
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

USER = 'quantumHamza2'
ROOT = Path(__file__).resolve().parents[1]


def api(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'Quantum-Lab-Profile'}
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    request = Request('https://api.github.com/' + path, headers=headers)
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def snapshot():
    repos = []
    for page in range(1, 11):
        batch = api(f'users/{USER}/repos?type=owner&per_page=100&page={page}')
        repos.extend(batch)
        if len(batch) < 100:
            break
    events = api(f'users/{USER}/events/public?per_page=100')
    standalone = [r for r in repos if not r['fork'] and r['name'] != USER]
    languages = Counter(r['language'] for r in standalone if r.get('language'))
    today = datetime.now(timezone.utc).date()
    days = [(today - timedelta(days=29-i)).isoformat() for i in range(30)]
    # Exclude profile maintenance to avoid a self-updating activity feedback loop.
    events = [e for e in events if e['repo']['name'] != f'{USER}/{USER}']
    counts = Counter(e['created_at'][:10] for e in events)
    return {'repositories': len(standalone), 'stars': sum(r['stargazers_count'] for r in standalone),
            'languages': sorted(languages.items(), key=lambda item: (-item[1], item[0])),
            'days': days, 'counts': [counts[d] for d in days],
            'latest': [{'repo': e['repo']['name'].split('/',1)[-1], 'type': e['type'].removesuffix('Event'), 'date': e['created_at'][:10]} for e in events[:3]]}


def render(data, timestamp):
    def txt(x,y,text,size=14,color='#a7bbcd',weight='normal'):
        return f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(str(text))}</text>'
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="390" viewBox="0 0 1000 390" role="img" aria-label="Public GitHub activity snapshot">',
             '<style>.beacon{animation:pulse 3s infinite}@keyframes pulse{50%{opacity:.3}}@media(prefers-reduced-motion:reduce){.beacon{animation:none}}</style>',
             '<rect x="1" y="1" width="998" height="388" rx="18" fill="#0b1421" stroke="#293d50"/>',
             '<circle cx="31" cy="34" r="4" fill="#70f0cd" class="beacon"/>',txt(45,39,'LAB PULSE / PUBLIC SIGNAL',12,'#70f0cd','bold'),
             txt(680,39,'Snapshot: '+timestamp,11,'#748da4'),
             txt(30,105,data['repositories'],40,'#f4f7fc','bold'),txt(30,132,'Standalone project repos',13),
             txt(273,105,data['stars'],40,'#f4f7fc','bold'),txt(273,132,'Stars on those repos',13),
             txt(503,91,'PRIMARY LANGUAGES',11,'#edc880','bold')]
    language_text = ' · '.join(f'{name} ({count})' for name,count in data['languages'][:4]) or 'No languages detected yet'
    parts += [txt(503,120,language_text,13),txt(503,141,'Count of repositories, not a skill score',11,'#748da4'),
              '<path d="M30 160H970" stroke="#293d50"/>',txt(30,187,'PUBLIC ACTIVITY / LAST 30 DAYS',11,'#70f0cd','bold'),
              txt(30,205,'Sampled from the latest 100 public events',10,'#748da4')]
    peak = max(data['counts'],default=0) or 1
    for i,count in enumerate(data['counts']):
        h = max(3,75*count/peak)
        parts.append(f'<rect x="{30+i*18}" y="{293-h}" width="12" height="{h}" rx="3" fill="{ "#70f0cd" if count else "#203143"}"><title>{data["days"][i]}: {count} sampled events</title></rect>')
    parts += [txt(30,316,data['days'][0],10,'#748da4'),txt(474,316,data['days'][-1],10,'#748da4'),txt(618,187,'RECENT TRANSMISSIONS',11,'#edc880','bold')]
    for i,event in enumerate(data['latest']):
        label = event['repo'] if len(event['repo']) <= 31 else event['repo'][:28]+'…'
        parts += [txt(618,216+i*41,label,13,'#e4eef8'),txt(618,232+i*41,event['type']+' / '+event['date'],10,'#748da4')]
    if not data['latest']:
        parts.append(txt(618,222,'No recent public events available',13))
    parts += ['<path d="M30 340H970" stroke="#293d50"/>',txt(30,366,'REAL DATA. SMALL ITERATIONS. CONTINUOUS LEARNING.',11,'#748da4'),'</svg>']
    return ''.join(parts)


def main():
    data = snapshot()  # On fetch failure, exit and preserve the last good card.
    state = ROOT/'assets/pulse-data.json'
    previous = json.loads(state.read_text()) if state.exists() else None
    if previous and previous.get('data') == data and (ROOT/'assets/pulse.svg').exists():
        print('Public data unchanged; no update required.')
        return
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    content = render(data, timestamp)
    import xml.etree.ElementTree as ET
    ET.fromstring(content)
    (ROOT/'assets/pulse.svg').write_text(content)
    state.write_text(json.dumps({'updated_at':timestamp,'data':data},indent=2)+'\n')
    print('Updated public profile activity snapshot.')

if __name__ == '__main__':
    main()
