"""Turn model scores into customer-ready cases: one message per business, with reasons and priority.

    python suggest.py            # writes work/cases.json (all businesses) + work/demo_cases.json (rich detail)
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import World, cycle, span  # noqa: E402
from messages import compose  # noqa: E402

W = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "work")
SNAP = date(2026, 11, 6)
THR, THR_CLOSED, ASK_LOW = 0.40, 0.55, 0.25
REG_CHANGE = re.compile(r"(numera|nykyään|nå bare|now only|changed|ändrats|muuttuneet|endret|gamla tider|vanhat ajat|gamle tider)", re.I)
SEASON_BREAK = re.compile(r"(\btauolla|talvitauo|vinterstängt|säsongsstängt|säsongsuppehåll|stengt for sesongen|sesongpause|winter break|closed for the season)", re.I)
TIME_RE = re.compile(r"(\d{1,2})[–-](\d{1,2})")


def hhmm(h):
    return f"{int(h):02d}:00"


class Suggester:
    def __init__(self, world=None, scored=None):
        self.w = world or World()
        self.df = scored if scored is not None else pd.read_parquet(f"{W}/scored_2026.parquet")
        self.groups = {k: g for k, g in self.df.groupby(["entity_id", "date"], sort=False)}
        self.by_ent = defaultdict(list)
        for (eid, d) in self.groups:
            self.by_ent[eid].append(d)

    # ---------- evidence ----------
    def evidence(self, eid, d: date, key, cand, row):
        w, ev = self.w, []
        cc = w.ents[eid]["meta"]["countryCode"]
        for back in (1, 2):
            for p in w.prev_dates(cc, key, d, back) if key not in ("EVENT", "SCHOOL_BREAK") else []:
                v, rr = w.entry(eid, p, SNAP)
                if v is not None:
                    vv = w.resolve(v, eid, p, SNAP)
                    ev.append({"type": f"ly{back}", "date": p.isoformat(), "hours": vv, "source": rr["source"],
                               "weight": 3 if back == 1 else 2})
                a, calls = w.analytics_signal(eid, p)
                if a is not None and a < 0.6:
                    ev.append({"type": "analytics", "date": p.isoformat(), "drop_pct": round(100 * (1 - a)), "weight": 2})
                c1, c2, texts = w.review_signals(eid, p, SNAP)
                if texts:
                    ev.append({"type": "review", "date": p.isoformat(), "text": texts[0][:140], "weight": 3})
                for (cr, h, st) in w.sugg.get((eid, p.isoformat()), []):
                    if cr < SNAP.isoformat():
                        ev.append({"type": "google_edit", "date": p.isoformat(), "hours": h, "weight": 1})
                if back == 1:
                    for pr in w.pilot.get((eid, p.isoformat()), []):
                        ev.append({"type": "pilot", "date": p.isoformat(), "decision": pr["decision"],
                                   "hours": pr["final_hours"] or pr["suggested_hours"], "weight": 2})
        mall = w.ents[eid].get("c_shoppingCenterEntityId")
        if mall:
            mv, _ = w.entry(mall, d, SNAP)
            if mv is not None:
                ev.append({"type": "mall", "name": w.ents[mall]["name"], "hours": w.resolve(mv, mall, d, SNAP), "weight": 4})
        pb = w.peer(eid, key)
        if pb and pb["closed_share_among_entered"]:
            ev.append({"type": "peers", "closed_pct": round(100 * float(pb["closed_share_among_entered"])),
                       "special": f"{pb['median_open_special']}-{pb['median_close_special']}" if pb["median_open_special"] else None,
                       "segment": w.ents[eid]["c_segment"], "weight": 1})
        for (cr, h, st) in w.sugg.get((eid, d.isoformat()), []):
            ev.append({"type": "google_edit_now", "hours": h, "weight": 2})
        # mark which evidence supports the proposed hours
        for e in ev:
            if e["type"] in ("ly1", "ly2", "mall", "google_edit", "google_edit_now", "pilot"):
                e["supports"] = e.get("hours") == cand or (e["type"] == "pilot" and e.get("hours") == cand)
            elif e["type"] in ("analytics", "review"):
                e["supports"] = cand == "closed"
            elif e["type"] == "peers":
                e["supports"] = (cand == "closed" and e["closed_pct"] >= 50) or cand == e.get("special")
        ev.sort(key=lambda e: (-int(e.get("supports", False)), -e["weight"]))
        return ev

    def expected_views(self, eid, d: date, key):
        """Search views at risk: same special day last year, else the business's average day."""
        cc = self.w.ents[eid]["meta"]["countryCode"]
        vals = []
        for p in self.w.prev_dates(cc, key, d, 1) if key not in ("EVENT", "SCHOOL_BREAK") else []:
            r = self.w.an.get((eid, p.isoformat()))
            if r:
                vals.append(r[0])
        if not vals:
            b = self.w.an_base.get(eid)
            vals = [b[2] * 1.2] if b else [5]
        return round(sum(vals) / len(vals), 1)

    # ---------- listing health (regular hours / seasonal break / closed for good) ----------
    def listing_health(self, eid):
        w, out = self.w, []
        n_rev, n_sug = w.perm_closed_signal(eid, SNAP)
        if n_rev or n_sug:
            txt = [r["content"] for r in w.reviews.get(eid, []) if r["_date"] > SNAP - timedelta(days=200)
                   and any(k in r["content"].lower() for k in ("lopett", "pysyv", "gott", "nedlagt", "closed down", "permanent", "lagt"))]
            out.append({"type": "CLOSED_FOR_GOOD", "reviews": n_rev, "google_edits": n_sug, "quote": txt[0][:140] if txt else None})
        recent = [r for r in w.reviews.get(eid, []) if r["_date"] > SNAP - timedelta(days=200) and r["content"]]
        rc = [r for r in recent if REG_CHANGE.search(r["content"])]
        wk = [s for s in w.sugg_weekly.get(eid, []) if s[0] > (SNAP - timedelta(days=200)).isoformat()]
        if rc or len(wk) >= 1 and rc:
            m = None
            for r in rc:
                m = TIME_RE.search(r["content"]) or m
            prop = f"{hhmm(m.group(1))}-{hhmm(m.group(2))}" if m else (wk[0][2] if wk else None)
            out.append({"type": "REGULAR_HOURS_CHANGED", "reviews": len(rc), "google_edits": len(wk),
                        "quote": rc[0]["content"][:140], "proposed_hours": prop,
                        "sunday_closed": any(re.search(r"(mån–lör|ma–la|man–lør|mon–sat)", r["content"], re.I) for r in rc)})
        sb = [r for r in w.reviews.get(eid, []) if r["_date"] > SNAP - timedelta(days=400) and r["content"]
              and SEASON_BREAK.search(r["content"])]
        if sb:
            out.append({"type": "SEASONAL_BREAK", "reviews": len(sb), "quote": sb[0]["content"][:140]})
        return out

    # ---------- the case ----------
    def case(self, eid, learning=None):
        w = self.w
        e = w.ents[eid]
        ct = w.contacts.get(eid, {})
        learning = learning or {}
        items, asks = [], []
        health = self.listing_health(eid)
        flagged = any(h["type"] == "CLOSED_FOR_GOOD" for h in health) and not e.get("closed")
        for ds in sorted(self.by_ent.get(eid, [])):
            g = self.groups[(eid, ds)]
            r0 = g.iloc[0]
            d = date.fromisoformat(ds)
            key = r0.key
            shown = r0.shown
            ps = g.loc[g.cand == shown, "p"].max()
            ns = g[g.cand != shown].sort_values("p", ascending=False)
            best = ns.iloc[0] if len(ns) else None
            name = w.cal_by.get((e["meta"]["countryCode"], ds), {})
            day_name = {"local": name.get("name_local", key.title()), "en": name.get("name_en", key.title())}
            # learning: owner said earlier how they handle this day → trust that first
            learned = learning.get(key)
            if learned and learned.get("decision") == "REJECTED":
                continue
            views = self.expected_views(eid, d, key)
            if learned and learned.get("hours") and learned["hours"] != shown:
                items.append({"date": ds, "key": key, "day_name": day_name, "shown": shown, "proposed": learned["hours"],
                              "confidence": 0.95, "views": views, "basis": "OWNER_PREVIOUS_ANSWER",
                              "evidence": [{"type": "owner_answer", "hours": learned["hours"], "supports": True, "weight": 5}]})
                continue
            if best is None:
                continue
            t = THR_CLOSED if best.cand == "closed" else THR
            if best.p >= t and best.p > ps:
                ev = self.evidence(eid, d, key, best.cand, r0)
                items.append({"date": ds, "key": key, "day_name": day_name, "shown": shown, "proposed": best.cand,
                              "confidence": round(float(best.p), 2), "views": views,
                              "basis": "+".join(s[4:] for s in g.columns if s.startswith("src_") and best[s] == 1),
                              "evidence": ev})
            elif best.p >= ASK_LOW and key in ("XMAS_EVE", "XMAS_DAY", "BOXING_DAY", "NYE", "NEW_YEARS_DAY", "EPIPHANY",
                                               "INDEPENDENCE_DAY", "MIDSUMMER_EVE") and r0.ly1_kind == "none" \
                    and (r0.hab_n or 0) == 0 and best.p >= 0.3:
                asks.append({"date": ds, "key": key, "day_name": day_name, "shown": shown, "best_guess": best.cand,
                             "confidence": round(float(best.p), 2), "views": views})
        for it in items:
            it["priority"] = round(it["confidence"] * it["views"] * (1.5 if it["proposed"] == "closed" else 1.0), 1)
        items.sort(key=lambda x: x["date"])
        mode = "FLAG" if flagged else ("OPTED_OUT" if ct.get("opted_out_of_suggestions") == "1" else
                                      ("AUTO_APPLY" if ct.get("standing_permission_holidays") == "1" and items else
                                       ("SUGGEST" if items else ("ASK" if asks else "QUIET"))))
        if mode == "AUTO_APPLY":
            # standing permission only covers confident, repeat patterns
            for it in items:
                it["auto"] = it["confidence"] >= 0.8 and any(x["type"] in ("ly1", "ly2", "mall", "owner_answer") and x.get("supports")
                                                           for x in it["evidence"])
        case = {
            "entity_id": eid, "name": e["name"], "city": e["address"]["city"], "country": e["meta"]["countryCode"],
            "segment": e["c_segment"], "customer_since": e.get("c_connectCustomerSince"),
            "mall": w.ents[e["c_shoppingCenterEntityId"]]["name"] if e.get("c_shoppingCenterEntityId") else None,
            "contact": {k: ct.get(k) for k in ("contact_first_name", "preferred_channel", "preferred_language",
                                               "best_contact_window", "standing_permission_holidays",
                                               "opted_out_of_suggestions")},
            "history_entries": len(w.hol_by_ent.get(eid, [])),
            "mode": mode, "items": items, "asks": asks[:3], "health": health,
            "views_at_risk": round(sum(i["views"] for i in items), 1),
            "priority": round(sum(i["priority"] for i in items), 1) + (50 if flagged else 0),
        }
        case["messages"] = compose(case)
        return case


def main():
    s = Suggester()
    allc = []
    demo_ids = sorted({eid for eid in s.by_ent if "-D" in eid})
    demo = {}
    for eid in s.by_ent:
        c = s.case(eid)
        allc.append({k: c[k] for k in ("entity_id", "name", "city", "country", "segment", "mode", "views_at_risk", "priority")}
                    | {"n_items": len(c["items"]), "n_asks": len(c["asks"]), "health": [h["type"] for h in c["health"]],
                       "channel": c["contact"]["preferred_channel"], "language": c["contact"]["preferred_language"]})
        if eid in demo_ids:
            demo[eid] = c
    allc.sort(key=lambda x: -x["priority"])
    # top test businesses get full detail too, for the ops queue
    for x in allc[:25]:
        demo.setdefault(x["entity_id"], s.case(x["entity_id"]))
    json.dump(allc, open(f"{W}/cases.json", "w"), ensure_ascii=False)
    json.dump(demo, open(f"{W}/demo_cases.json", "w"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(x["mode"] for x in allc), sum(x["n_items"] for x in allc))


if __name__ == "__main__":
    main()
