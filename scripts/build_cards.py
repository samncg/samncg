"""Generate ASCII-style stat cards for the profile README.

Uses only the standard library. Needs GITHUB_TOKEN (the Actions token is enough)
and optionally GH_USER (defaults to samncg). Writes assets/generated/*.svg
"""
import datetime as dt
import json
import os
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "samncg")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "generated")

QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes {
        name stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

THEMES = {
    "dark": dict(bg="#000000", line="#262626", ink="#ededed", sub="#a3a3a3", faint="#5a5a5a",
                 empty="#262626", accent="#c4b2ff", levels=["#4a3a85", "#6d55c9", "#9378ff", "#c4b2ff"],
                 cell="#161616", heat=["#4b2386", "#c23a6b", "#f07f2d", "#ffd65c"]),
    "light": dict(bg="#ffffff", line="#d0d7de", ink="#121212", sub="#4a4a4a", faint="#9a9a9a",
                  empty="#d9d9d9", accent="#3c2899", levels=["#c7baf5", "#9a82ea", "#6b4fd8", "#3c2899"],
                  cell="#ebedf0", heat=["#7a4fd0", "#d6457a", "#f0832a", "#e8b100"]),
}
FONT = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(json.dumps(data["errors"]))
    return data["data"]["user"]


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    cur = 0
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:
        i -= 1  # today may simply not have started yet
    while i >= 0 and counts[i]:
        cur += 1
        i -= 1
    return cur, longest


def frame(t, w, h, title, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">
  <title>{escape(title)}</title>
  <style>
    text {{ font-family: {FONT}; font-size: 12.5px; white-space: pre; fill: {t["sub"]}; }}
    .ink {{ fill: {t["ink"]}; }} .faint {{ fill: {t["faint"]}; }} .accent {{ fill: {t["accent"]}; }}
    .title {{ fill: {t["ink"]}; font-weight: 700; font-size: 13.5px; }}
    .row {{ opacity: 0; animation: in .6s ease-out forwards; }}
    @keyframes in {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: none; }} }}
    @media (prefers-reduced-motion: reduce) {{ .row {{ animation: none; opacity: 1; }} }}
  </style>
  <rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{t["bg"]}" stroke="{t["line"]}"/>
  <text class="title" x="22" y="34">{escape(title)}</text>
  {body}
</svg>
'''


def leader(label, value, width=46):
    dots = "." * max(2, width - len(label) - len(value) - 2)
    return label, dots, value


def stats_card(u, t):
    cc = u["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    cur, longest = streaks(days)
    repos = u["repositories"]
    stars = sum(r["stargazerCount"] for r in repos["nodes"])
    since = u["createdAt"][:4]
    rows = [
        ("contributions (1y)", str(cc["contributionCalendar"]["totalContributions"])),
        ("commits (1y)", str(cc["totalCommitContributions"])),
        ("public repos", str(repos["totalCount"])),
        ("stars earned", str(stars)),
        ("current streak", f"{cur}d"),
        ("longest streak", f"{longest}d"),
        ("on github since", since),
    ]
    body = []
    for i, (k, v) in enumerate(rows):
        label, dots, value = leader(k, v)
        y = 66 + i * 21
        body.append(
            f'<g class="row" style="animation-delay:{i * 0.08:.2f}s">'
            f'<text x="22" y="{y}"><tspan class="faint">&gt; </tspan>{escape(label)} '
            f'<tspan class="faint">{dots}</tspan> <tspan class="{"accent" if "streak" in k else "ink"}">{escape(value)}</tspan></text></g>'
        )
    return frame(t, 480, 222, f"~/{USER}/stats", "\n  ".join(body))


def langs_card(u, t):
    # each repo contributes its own language mix once, so one repo full of generated
    # files (e.g. built HTML) cannot drown out everything else
    sizes = {}
    for r in u["repositories"]["nodes"]:
        edges = r["languages"]["edges"]
        repo_total = sum(e["size"] for e in edges)
        for e in edges:
            if repo_total:
                sizes[e["node"]["name"]] = sizes.get(e["node"]["name"], 0) + e["size"] / repo_total
    total = sum(sizes.values()) or 1
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[:7]
    body = []
    bar_w = 22
    for i, (name, size) in enumerate(top):
        pct = size / total * 100
        fill = max(1, round(bar_w * size / top[0][1]))
        bar = "#" * fill
        rest = "-" * (bar_w - fill)
        y = 66 + i * 21
        body.append(
            f'<g class="row" style="animation-delay:{i * 0.08:.2f}s">'
            f'<text x="22" y="{y}"><tspan class="ink">{escape(name[:12].ljust(12))}</tspan> '
            f'<tspan class="faint">[</tspan><tspan class="{"accent" if i == 0 else "ink"}">{bar}</tspan>'
            f'<tspan class="faint">{rest}]</tspan> {pct:5.1f}%</text></g>'
        )
    return frame(t, 480, 222, f"~/{USER}/languages", "\n  ".join(body))


def heat_card(u, t):
    """Contribution calendar as squares on a thermal scale: cool purple for light days, through red and
    orange, to hot yellow for the busiest (levels are quartiles of your own non-zero days)."""
    cal = u["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    counts = sorted(d["contributionCount"] for w in weeks for d in w["contributionDays"] if d["contributionCount"])
    q = lambda p: counts[min(len(counts) - 1, int(len(counts) * p))] if counts else 1
    cuts = [q(0.25), q(0.5), q(0.8)]
    cell, gap, x0, y0 = 14, 4, 24, 58
    step = cell + gap
    body = []
    months, last_month = [], None
    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            day = dt.date.fromisoformat(d["date"])
            c = d["contributionCount"]
            lvl = 0 if c == 0 else 1 if c <= cuts[0] else 2 if c <= cuts[1] else 3 if c <= cuts[2] else 4
            x = x0 + wi * step
            y = y0 + day.isoweekday() % 7 * step
            col = t["cell"] if lvl == 0 else t["heat"][lvl - 1]
            delay = wi * 0.012
            # colour goes in the style attribute so no stylesheet rule can override it
            body.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" class="row" '
                        f'style="fill:{col};animation-delay:{delay:.2f}s"><title>{c} on {d["date"]}</title></rect>')
            if day.day <= 7 and day.isoweekday() % 7 == 0 and day.month != last_month:
                months.append((x, day.strftime("%b").lower()))
                last_month = day.month
    for x, m in months:
        body.append(f'<text class="faint" x="{x}" y="{y0 - 8}">{m}</text>')
    total = cal["totalContributions"]
    legend_y = y0 + 7 * step + 24
    body.append(f'<text x="{x0}" y="{legend_y}"><tspan class="ink">{total}</tspan> contributions in the last year</text>')
    right = x0 + len(weeks) * step - gap
    swatches = [t["cell"]] + t["heat"]
    sx = right - 40 - len(swatches) * step
    body.append(f'<text class="faint" x="{sx - 8}" y="{legend_y}" text-anchor="end">less</text>')
    for i, col in enumerate(swatches):
        body.append(f'<rect x="{sx + i * step}" y="{legend_y - 11}" width="{cell}" height="{cell}" rx="3" style="fill:{col}"/>')
    body.append(f'<text class="faint" x="{sx + len(swatches) * step + 4}" y="{legend_y}">more</text>')
    w = x0 * 2 + len(weeks) * step - gap
    return frame(t, w, legend_y + 22, f"~/{USER}/contributions", "\n  ".join(body))


TOOLS = [
    ("languages", ["java", "c#", "python", "kotlin", "javascript", "rust (learning)"]),
    ("build", ["react", "vite", "jetpack compose", "godot", "webgl"]),
    ("make", ["cad", "kicad", "blender", "3d printing", "pla/petg/abs/asa/tpu"]),
    ("ai", ["local llms", "comfyui", "agents"]),
]


def tools_card(u, t):
    body = []
    for i, (group, items) in enumerate(TOOLS):
        y = 66 + i * 26
        chips = []
        for it in items:
            chips.append(f'<tspan class="faint">[</tspan><tspan class="ink">{escape(it)}</tspan><tspan class="faint">]</tspan>')
        body.append(
            f'<g class="row" style="animation-delay:{i * 0.1:.2f}s">'
            f'<text x="22" y="{y}"><tspan class="accent">{escape(group.ljust(10))}</tspan> ' + " ".join(chips) + "</text></g>"
        )
    return frame(t, 980, 66 + len(TOOLS) * 26 + 6, f"~/{USER}/toolbox", "\n  ".join(body))


def main():
    if not TOKEN:
        raise SystemExit("GITHUB_TOKEN is not set")
    u = fetch()
    os.makedirs(OUT, exist_ok=True)
    for name, t in THEMES.items():
        for card, fn in (("stats", stats_card), ("langs", langs_card), ("heatmap", heat_card), ("toolbox", tools_card)):
            with open(os.path.join(OUT, f"{card}-{name}.svg"), "w", encoding="utf-8") as fh:
                fh.write(fn(u, t))
    print("cards written to", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
