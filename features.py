"""Connect Suggests – feature + candidate engine.

For every (entity, special day) it builds the set of candidate hours that the data supports
(shown now, last year's exception, two years ago, shopping centre, peers, Google user edits,
complaint reviews, pilot decisions …) together with the evidence behind each candidate.
The same evidence is reused by the ranker (ML) and by the customer message (explanations).
"""
from __future__ import annotations

import csv
import json
import os
import re
from collections import defaultdict
from datetime import date, datetime, timedelta

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DATA_ROOT = os.environ.get("CONNECT_DATA", "/home/claude/src/Fonecta_SinceAI2026/data/FONECTA_CONNECT_SUGGESTS_2026")
D = lambda *p: os.path.join(DATA_ROOT, *p)  # noqa: E731

PERM_WORDS = ("lopettanut", "pysyvästi", "lopettaneet", "stängt för gott", "lagt ned", "slått igen", "stengt for godt",
              "closed down", "permanently closed", "closed for good", "konkurs", "lagt ner", "nedlagt")
CLOSED_COMPLAINT = re.compile(r"(kiinni|suljettu|suljetun|stängt|stängd|stengt|closed|lukossa)", re.I)
WRONG_HOURS = re.compile(r"(aukioloa|öppettid|åpningstid|opening hours|hours were wrong|väärin|fel tider|feil)", re.I)


def day_str(obj):
    if not obj or obj.get("isClosed"):
        return "closed"
    return ",".join(f"{i['start']}-{i['end']}" for i in obj.get("openIntervals", [])) or "closed"


def cycle(d: date):
    return d.year if d.month >= 2 else d.year - 1


def to_min(s):
    return int(s[:2]) * 60 + int(s[3:])


def span(h):
    """(open_min, close_min, total_minutes) or None for closed."""
    if h in (None, "", "closed", "REGULAR"):
        return None
    ivs = []
    for iv in h.split(","):
        a, b = iv.split("-")
        sa, sb = to_min(a), to_min(b)
        if sb <= sa:
            sb += 1440
        ivs.append((sa, sb))
    return ivs[0][0], ivs[-1][1], sum(b - a for a, b in ivs)


class World:
    """All data Connect knows, loaded once."""

    def __init__(self):
        self.ents = {e["meta"]["id"]: e for e in
                     json.load(open(D("data", "entities.json"), encoding="utf-8"))["response"]["entities"]}
        self.hol = defaultdict(list)
        self.hol_by_ent = defaultdict(list)
        for line in open(D("data", "holiday_hours_history.jsonl"), encoding="utf-8"):
            r = json.loads(line)
            self.hol[(r["entity_id"], r["date"])].append(r)
            self.hol_by_ent[r["entity_id"]].append(r)
        self.reg = defaultdict(list)
        for line in open(D("data", "regular_hours_history.jsonl"), encoding="utf-8"):
            r = json.loads(line)
            self.reg[r["entity_id"]].append(r)
        self.cal = list(csv.DictReader(open(D("data", "calendar_special_days.csv"), encoding="utf-8")))
        self.cal_by = {(r["country"], r["date"]): r for r in self.cal}
        self.dates_by_key = defaultdict(list)
        for r in self.cal:
            self.dates_by_key[(r["country"], r["day_key"])].append(date.fromisoformat(r["date"]))
        self.bench = {(r["country"], r["city_tier"], r["segment"], r["day_key"]): r
                      for r in csv.DictReader(open(D("data", "peer_benchmarks.csv"), encoding="utf-8"))}
        self.tiers = {r["city"]: r["city_tier"] for r in csv.DictReader(open(D("data", "cities.csv"), encoding="utf-8"))}
        self.contacts = {r["entity_id"]: r for r in csv.DictReader(open(D("data", "customer_contacts.csv"), encoding="utf-8"))}
        self.pilot = defaultdict(list)
        self.pilot_by_ent = defaultdict(list)
        for r in csv.DictReader(open(D("data", "pilot_decision_log_2025.csv"), encoding="utf-8")):
            self.pilot[(r["entity_id"], r["date"])].append(r)
            self.pilot_by_ent[r["entity_id"]].append(r)
        rev = json.load(open(D("data", "reviews.json"), encoding="utf-8"))["response"]["reviews"]
        self.reviews = defaultdict(list)
        for r in rev:
            r["_date"] = datetime.utcfromtimestamp(r["publisherDate"] / 1000).date()
            self.reviews[r["locationId"]].append(r)
        sg = json.load(open(D("data", "publisher_suggestions.json"), encoding="utf-8"))["response"]["suggestions"]
        self.sugg = defaultdict(list)          # (eid, date) -> [(created, hours, status)]
        self.sugg_closed = defaultdict(list)   # eid -> [(created, status)]
        self.sugg_weekly = defaultdict(list)   # eid -> [(created, weekday, hours, status)]
        for s in sg:
            try:
                sc = json.loads(s["suggestedContent"])
            except Exception:
                continue
            if s["fieldName"] == "closed":
                self.sugg_closed[s["locationId"]].append((s["dateCreated"], s["status"]))
                continue
            for hh in sc.get("holidayHours", []) or []:
                self.sugg[(s["locationId"], hh["date"])].append((s["dateCreated"], day_str(hh), s["status"]))
            for dname in DAYS:
                if dname in sc:
                    self.sugg_weekly[s["locationId"]].append((s["dateCreated"], dname, day_str(sc[dname]), s["status"]))
        self._events = None
        self._load_analytics()

    def _load_analytics(self):
        import numpy as np
        import pandas as pd
        A = pd.read_parquet(D("data", "analytics_daily.parquet"),
                            columns=["date", "entity_id", "GOOGLE_SEARCH_VIEWS", "GOOGLE_CUSTOMER_ACTIONS", "GOOGLE_PHONE_CALLS"])
        A["date"] = pd.to_datetime(A["date"]).dt.strftime("%Y-%m-%d")
        A["apv"] = A.GOOGLE_CUSTOMER_ACTIONS / (A.GOOGLE_SEARCH_VIEWS + 1)
        self.an = {(e, d): (v, a, c, p) for e, d, v, a, c, p in zip(A.entity_id, A.date, A.GOOGLE_SEARCH_VIEWS,
                                                                   A.GOOGLE_CUSTOMER_ACTIONS, A.GOOGLE_PHONE_CALLS, A.apv)}
        g = A.groupby("entity_id")
        self.an_base = {e: (float(x.apv.median()), float(x.GOOGLE_PHONE_CALLS.mean()) + 0.1, float(x.GOOGLE_SEARCH_VIEWS.mean()))
                        for e, x in g}
        self._np = np

    def analytics_signal(self, eid, day: date):
        """Ratio of customer actions per view, and calls, vs the business's normal level on a past day.
        Real closures show up as ~half the usual actions per view and slightly more phone calls."""
        r = self.an.get((eid, day.isoformat()))
        if r is None:
            return None, None
        loc = [self.an.get((eid, (day + timedelta(days=k)).isoformat())) for k in (-14, -7, 7, 14)]
        loc = [x for x in loc if x is not None]
        if not loc:
            return None, None
        acts = sorted(x[1] for x in loc)[len(loc) // 2]
        calls = sum(x[2] for x in loc) / len(loc)
        return r[1] / (acts + 0.5), r[2] - calls

    def holiday_closure_profile(self, eid, as_of: date, country: str):
        """Across all public holidays of the previous season: share of days that *look* closed in analytics."""
        rs = []
        for r in self.cal:
            if r["country"] != country or r["day_type"] not in ("PUBLIC_HOLIDAY", "EVE"):
                continue
            dd = date.fromisoformat(r["date"])
            if as_of - timedelta(days=400) <= dd < as_of - timedelta(days=3):
                a, _ = self.analytics_signal(eid, dd)
                if a is not None:
                    rs.append(a)
        if not rs:
            return None, None
        return sum(rs) / len(rs), sum(1 for x in rs if x < 0.6) / len(rs)

    # ---------- basic lookups ----------
    def regular(self, eid, d: date, as_of: date):
        cands = [r for r in self.reg[eid] if r["effective_from"] == "before-2024" or r["effective_from"] < as_of.isoformat()]
        if not cands:
            return day_str(self.ents[eid]["hours"].get(DAYS[d.weekday()]))
        # the version in force on day d (seasonal closures) but known at as_of
        valid = [r for r in cands if r["effective_from"] == "before-2024" or r["effective_from"] <= d.isoformat()]
        pool = valid or cands
        best = max(pool, key=lambda r: "0000" if r["effective_from"] == "before-2024" else r["effective_from"])
        return day_str(best["hours"][DAYS[d.weekday()]])

    def entry(self, eid, d: date, as_of: date, include_late=True):
        rows = [r for r in self.hol.get((eid, d.isoformat()), []) if r["entered_at"] < as_of.isoformat()]
        if not include_late:
            rows = [r for r in rows if r["entered_at"] < d.isoformat()]
        if not rows:
            return None, None
        r = max(rows, key=lambda r: r["entered_at"])
        h = r["holidayHours"]
        return ("REGULAR" if h.get("isRegularHours") else day_str(h)), r

    def resolve(self, val, eid, d, as_of):
        if val is None:
            return None
        return self.regular(eid, d, as_of) if val == "REGULAR" else val

    def displayed(self, eid, d, as_of):
        e, _ = self.entry(eid, d, as_of, include_late=False) if d < as_of else self.entry(eid, d, as_of)
        if e is None or e == "REGULAR":
            return self.regular(eid, d, as_of)
        return e

    def prev_dates(self, country, key, d, back=1):
        """Same special day `back` cycles earlier. For INTERDAY / multi-date keys pick the same day-of-month."""
        target = cycle(d) - back
        xs = [x for x in self.dates_by_key[(country, key)] if cycle(x) == target]
        if not xs:
            return []
        if len(xs) == 1:
            return xs
        same = [x for x in xs if (x.month, x.day) == (d.month, d.day)]
        if same:
            return same
        return [min(xs, key=lambda x: abs((x.replace(year=2000) - d.replace(year=2000)).days))]

    def peer(self, eid, key):
        e = self.ents[eid]
        return self.bench.get((e["meta"]["countryCode"], self.tiers.get(e["address"]["city"], "town"), e["c_segment"], key))

    # ---------- signals ----------
    def review_signals(self, eid, past_day: date, as_of: date):
        """Complaint reviews written 0–4 days after a past special day."""
        closed = wrong = 0
        texts = []
        for r in self.reviews.get(eid, []):
            if r["_date"] >= as_of:
                continue
            dd = (r["_date"] - past_day).days
            if 0 <= dd <= 4 and r["content"]:
                c = r["content"]
                if CLOSED_COMPLAINT.search(c) and r["rating"] <= 3:
                    closed += 1
                    texts.append(c)
                elif WRONG_HOURS.search(c) and r["rating"] <= 3:
                    wrong += 1
                    texts.append(c)
        return closed, wrong, texts

    def perm_closed_signal(self, eid, as_of: date):
        cut = as_of - timedelta(days=200)
        n_rev = sum(1 for r in self.reviews.get(eid, []) if cut <= r["_date"] < as_of and
                    any(w in r["content"].lower() for w in PERM_WORDS))
        n_sug = sum(1 for (c, st) in self.sugg_closed.get(eid, []) if c < as_of.isoformat() and c >= cut.isoformat())
        return n_rev, n_sug

    def diligence(self, eid, as_of: date):
        """How often the owner enters exceptions themselves, and how early."""
        rows = [r for r in self.hol_by_ent.get(eid, []) if r["entered_at"] < as_of.isoformat()]
        own = [r for r in rows if r["source"] in ("OWNER_UI", "FONECTA_SUPPORT")]
        lead = [(date.fromisoformat(r["date"]) - date.fromisoformat(r["entered_at"][:10])).days for r in own]
        return len(rows), len(own), (sorted(lead)[len(lead) // 2] if lead else -1)
