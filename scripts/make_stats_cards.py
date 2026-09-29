#!/usr/bin/env python3
"""Regenere les cartes de stats du profil (SVG maison, palette CRT ambre/phosphore vert).

    python3 scripts/make_stats_cards.py            # API publique (rate-limit ~60 req/h)
    GITHUB_TOKEN=ghp_xxx python3 scripts/make_stats_cards.py   # si rate-limit atteint

Ecrit assets/stats-card.svg et assets/languages-card.svg depuis les vraies donnees GitHub.
Aucune dependance : urllib seulement.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

USER = "Mehdo0"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
AMBER = "#ffb000"
DIM = "#b87400"
GREEN = "#26ff6a"
TEXT = "#d7d2c4"
RED = "#ff3b1f"
BG = "#0b0f0d"
FONT = "ui-monospace, 'Courier New', monospace"

PLOT = ["Python", "C", "C++", "TypeScript", "JavaScript", "Shell", "HTML", "CSS", "Jupyter Notebook", "Other"]


def gh(path: str) -> dict | list:
    req = urllib.request.Request(f"https://api.github.com{path}",
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": "mehdo0-profile-cards"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


CACHE = OUT / "stats-cache.json"


def collect() -> dict:
    """Interroge l'API GitHub ; si le rate-limit frappe, retombe sur le cache local."""
    try:
        data = collect_api()
    except urllib.error.HTTPError as e:
        if not CACHE.exists():
            raise
        print(f"API GitHub indisponible ({e.code}) — cartes generees depuis {CACHE.name}")
        return json.loads(CACHE.read_text())
    CACHE.write_text(json.dumps(data))
    return data


def collect_api() -> dict:
    user = gh(f"/users/{USER}")
    repos = [r for r in gh(f"/users/{USER}/repos?per_page=100&sort=updated") if not r["fork"]]
    langs: dict[str, int] = {}
    for r in repos:
        try:
            for k, v in gh(f"/repos/{USER}/{r['name']}/languages").items():
                langs[k] = langs.get(k, 0) + int(v)
        except urllib.error.HTTPError:
            continue
    top = sorted(repos, key=lambda r: (-r["stargazers_count"], r["name"]))[:4]
    return {"user": user, "repos": repos, "langs": langs, "top": top}


def head(w: int, h: int, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{title}">\n<title>{title}</title>\n'
            f'<defs><pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
            f'<rect width="4" height="1.3" fill="#000000" opacity="0.45"/></pattern>'
            f'<linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0%" stop-color="{DIM}"/><stop offset="100%" stop-color="{AMBER}"/></linearGradient></defs>\n'
            f'<rect width="{w}" height="{h}" rx="12" fill="{BG}"/>\n'
            f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="11" fill="none" stroke="{AMBER}" stroke-opacity="0.55" stroke-width="1.4"/>\n'
            f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="11" fill="url(#scan)" opacity="0.35"/>\n'
            f'<text x="22" y="34" font-family="{FONT}" font-size="14" font-weight="700" fill="{AMBER}" letter-spacing="2">{title}</text>\n'
            f'<rect x="22" y="42" width="{w-44}" height="1" fill="{AMBER}" opacity="0.35"/>\n')


def stats_card(d: dict) -> str:
    u, repos, top, langs = d["user"], d["repos"], d["top"], d["langs"]
    stars = sum(r["stargazers_count"] for r in repos)
    code_mb = sum(langs.values()) / 1_048_576
    rows = [("PUBLIC REPOS", str(u["public_repos"])),
            ("TOTAL STARS", str(stars)),
            ("CODE VOLUME", f"{code_mb:.1f} MB"),
            ("FOLLOWERS", str(u["followers"])),
            ("MEMBER SINCE", u["created_at"][:4]),
            ("LAST PUSH", max(r["pushed_at"] for r in repos)[:10])]
    w, h = 470, 96 + 30 * len(rows) + 34 + 20 * len(top)
    s = head(w, h, "> STATS DUMP")
    y = 76
    for label, val in rows:
        s += (f'<text x="26" y="{y}" font-family="{FONT}" font-size="13" fill="{GREEN}">{label}</text>\n'
              f'<text x="{w-26}" y="{y}" text-anchor="end" font-family="{FONT}" font-size="14" font-weight="700" '
              f'fill="{AMBER}">{val}</text>\n'
              f'<rect x="26" y="{y+7}" width="{w-52}" height="1" fill="{TEXT}" opacity="0.12"/>\n')
        y += 30
    y += 8
    s += f'<text x="26" y="{y}" font-family="{FONT}" font-size="13" fill="{GREEN}">TOP LOOT</text>\n'
    y += 20
    for r in top:
        s += (f'<text x="26" y="{y}" font-family="{FONT}" font-size="12" fill="{TEXT}">'
              f'{r["name"]}</text>\n'
              f'<text x="{w-26}" y="{y}" text-anchor="end" font-family="{FONT}" font-size="12" fill="{AMBER}">'
              f'★ {r["stargazers_count"]} · {r.get("language") or "—"}</text>\n')
        y += 19
    return s + "</svg>\n"


def langs_card(d: dict) -> str:
    langs = d["langs"]
    total = sum(langs.values()) or 1
    items = sorted(langs.items(), key=lambda kv: -kv[1])[:8]
    w = 470
    h = 96 + 30 * len(items)
    s = head(w, h, "> TECH SPLIT (bytes)")
    y = 78
    for name, size in items:
        pct = size / total * 100
        barw = int((w - 210) * pct / 100)
        s += (f'<text x="26" y="{y-2}" font-family="{FONT}" font-size="12" fill="{TEXT}">{name}</text>\n'
              f'<rect x="170" y="{y-13}" width="{w-210}" height="12" rx="3" fill="{TEXT}" opacity="0.10"/>\n'
              f'<rect x="170" y="{y-13}" width="{barw}" height="12" rx="3" fill="url(#bar)"/>\n'
              f'<text x="{w-26}" y="{y-2}" text-anchor="end" font-family="{FONT}" font-size="12" fill="{AMBER}">'
              f'{pct:4.1f}%</text>\n')
        y += 30
    s += (f'<text x="26" y="{h-14}" font-family="{FONT}" font-size="11" fill="{GREEN}" opacity="0.8">'
          f'from {len(d["repos"])} public repos · make_stats_cards.py</text>\n')
    return s + "</svg>\n"


def main() -> int:
    d = collect()
    OUT.mkdir(exist_ok=True)
    (OUT / "stats-card.svg").write_text(stats_card(d))
    (OUT / "languages-card.svg").write_text(langs_card(d))
    print(f"assets/stats-card.svg + assets/languages-card.svg ecrits "
          f"({len(d['repos'])} repos, {sum(d['langs'].values()) / 1_048_576:.1f} MB de code)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
