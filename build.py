"""Build candidate-level training / prediction tables for a season."""
from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import World, D, cycle, span, day_str  # noqa: E402

SNAP = {2024: date(2024, 11, 6), 2025: date(2025, 11, 6), 2026: date(2026, 11, 6)}
KEYS = ["XMAS_EVE", "XMAS_DAY", "BOXING_DAY", "DEC23", "INTERDAY", "NYE", "NEW_YEARS_DAY", "EPIPHANY_EVE", "EPIPHANY",
        "INDEPENDENCE_DAY", "FATHERS_DAY", "LUCIA", "BLACK_FRIDAY", "EVENT", "SCHOOL_BREAK"]
EVE_KEYS = {"XMAS_EVE", "NYE", "EPIPHANY_EVE", "DEC23", "INTERDAY"}


def fmt(o, c):
    c = c % 1440 if c >= 1440 else c
    return f"{o // 60:02d}:{o % 60:02d}-{c // 60:02d}:{c % 60:02d}"


SOURCES = ["shown", "closed", "reg", "ly1", "ly2", "mall", "peer", "sugg_now", "sugg_ly1", "pilot", "sib", "rev_ly1",
           "reg_m60", "reg_p60", "reg_m120", "ly1_rel", "peer_close", "peer_open", "an_ly1", "eve_mode", "eve_close", "spec_mode"]


def kind(v, reg):
    if v is None:
        return "none"
    if v == "closed":
        return "closed"
    if v == reg:
        return "regular"
    return "special"


def targets(season):
    if season == 2026:
        rows = list(csv.DictReader(open(D("evaluation", "targets_2026.csv"), encoding="utf-8")))
        lab = {(r["entity_id"], r["date"]): r for r in csv.DictReader(open(D("labels", "dev_labels_2026.csv"), encoding="utf-8"))}
    elif season == 2025:
        rows = list(csv.DictReader(open(D("evaluation", "targets_2025_backtest.csv"), encoding="utf-8")))
        lab = {(r["entity_id"], r["date"]): r for r in csv.DictReader(open(D("labels", "dev_labels_2025_backtest.csv"), encoding="utf-8"))}
    else:  # 2024 season from dev truth history
        lab, rows = {}, []
        for r in csv.DictReader(open(D("labels", "dev_truth_history.csv"), encoding="utf-8")):
            d = date.fromisoformat(r["date"])
            if date(2024, 11, 7) <= d <= date(2025, 1, 6) and r["day_key"] in KEYS:
                rows.append({"entity_id": r["entity_id"], "date": r["date"], "day_key": r["day_key"],
                             "event_id": r["event_id"], "split": "dev", "day_type": ""})
                lab[(r["entity_id"], r["date"])] = {"truth_hours": r["truth_hours"]}
    return rows, lab


def build(world: World, season: int, only_split=None):
    snap = SNAP[season]
    rows, lab = targets(season)
    out = []
    perm_cache, dil_cache, habit_cache = {}, {}, {}
    for r in rows:
        if only_split and r["split"] not in only_split:
            continue
        eid, d, key = r["entity_id"], date.fromisoformat(r["date"]), r["day_key"]
        e = world.ents[eid]
        cc = e["meta"]["countryCode"]
        reg = world.regular(eid, d, snap)
        shown = world.displayed(eid, d, snap)
        now_entry, _ = world.entry(eid, d, snap)
        cands = defaultdict(set)
        cands[shown].add("shown")
        cands["closed"].add("closed")
        cands[reg].add("reg")
        f = {}
        # last years
        for back in (1, 2):
            pv = world.prev_dates(cc, key, d, back) if key not in ("EVENT", "SCHOOL_BREAK") else []
            val = None
            late = 0
            rc = rw = 0
            sug_ly = None
            for p in pv:
                v, rr = world.entry(eid, p, snap)
                if v is not None:
                    val = world.resolve(v, eid, d, snap) if v == "REGULAR" else v
                    late = int(rr["entered_at"][:10] >= p.isoformat())
                    f[f"ly{back}_src_{rr['source']}"] = 1
                c1, c2, _ = world.review_signals(eid, p, snap)
                ar, cr_ = world.analytics_signal(eid, p) if p < snap - timedelta(days=3) else (None, None)
                f[f"ly{back}_act_loc"], f[f"ly{back}_calls_diff"] = ar, cr_
                if back == 1 and ar is not None and ar < 0.5:
                    cands["closed"].add("an_ly1")
                rc += c1
                rw += c2
                for (cr, h, st) in world.sugg.get((eid, p.isoformat()), []):
                    if cr < snap.isoformat():
                        sug_ly = h
                if back == 1:
                    for pr in world.pilot.get((eid, p.isoformat()), []):
                        if pr["sent_at"] < snap.isoformat():
                            f["pilot_decision"] = pr["decision"]
                            fh = pr["final_hours"] or (pr["suggested_hours"] if pr["decision"] == "ACCEPTED" else "")
                            if fh and pr["decision"] in ("ACCEPTED", "EDITED"):
                                cands[fh].add("pilot")
                            f["pilot_rejected"] = int(pr["decision"] == "REJECTED")
                            f["standing_perm"] = int(pr["standing_permission_granted"] == "True")
            f[f"ly{back}_kind"] = kind(val, reg)
            f[f"ly{back}_late"] = late
            f[f"ly{back}_rev_closed"] = rc
            f[f"ly{back}_rev_wrong"] = rw
            f[f"ly{back}_sugg_kind"] = kind(sug_ly, reg)
            if val is not None:
                cands[val].add(f"ly{back}")
            if back == 1 and sug_ly is not None:
                cands[sug_ly].add("sugg_ly1")
            if back == 1 and rc > 0:
                cands["closed"].add("rev_ly1")
        # this year's google user edit for this exact date
        for (cr, h, st) in world.sugg.get((eid, d.isoformat()), []):
            if cr < snap.isoformat():
                cands[h].add("sugg_now")
                f["sugg_now_status"] = st
        # shopping centre
        mall = e.get("c_shoppingCenterEntityId")
        f["has_mall"] = int(bool(mall))
        if mall:
            mv, _ = world.entry(mall, d, snap)
            mv = world.resolve(mv, mall, d, snap) if mv else None
            if mv is not None:
                cands[mv].add("mall")
            f["mall_kind"] = kind(mv, reg)
            # did the business follow its mall last year?
            pv = world.prev_dates(cc, key, d, 1) if key not in ("EVENT", "SCHOOL_BREAK") else []
            fol = -1
            for p in pv:
                a, _ = world.entry(eid, p, snap)
                b, _ = world.entry(mall, p, snap)
                if a is not None and b is not None:
                    fol = int(world.resolve(a, eid, p, snap) == world.resolve(b, mall, p, snap))
            f["mall_followed_ly"] = fol
        # siblings (other INTERDAY dates this season already entered)
        if key == "INTERDAY":
            for off in (-2, -1, 1, 2):
                sd = d + timedelta(days=off)
                sv, _ = world.entry(eid, sd, snap)
                if sv is not None and world.cal_by.get((cc, sd.isoformat()), {}).get("day_key") == "INTERDAY":
                    cands[world.resolve(sv, eid, sd, snap)].add("sib")
        # shifted variants of regular hours (same open, earlier / later close)
        if sp_reg0 := span(reg):
            o, c_, _ = sp_reg0
            for dlt, tag in ((-60, "reg_m60"), (60, "reg_p60"), (-120, "reg_m120")):
                cands[fmt(o, c_ + dlt)].add(tag)
        # last year's special hours, re-applied relative to this year's regular hours
        for p in (world.prev_dates(cc, key, d, 1) if key not in ("EVENT", "SCHOOL_BREAK") else []):
            v, _ = world.entry(eid, p, snap)
            sp_v, sp_rp = span(v) if v not in (None, "REGULAR") else None, span(world.regular(eid, p, snap))
            if sp_v and sp_rp and span(reg):
                o2 = span(reg)[0] + (sp_v[0] - sp_rp[0])
                c2 = span(reg)[1] + (sp_v[1] - sp_rp[1])
                if 0 <= o2 < c2:
                    cands[fmt(o2, c2)].add("ly1_rel")
        # owner's habitual special hours on eve-type days (same hours reused across eves ~77 %)
        ek = (eid, season, "eve")
        if ek not in habit_cache:
            from collections import Counter
            ev_c, sp_c = Counter(), Counter()
            for hr in world.hol_by_ent.get(eid, []):
                if hr["entered_at"] >= snap.isoformat() or hr["holidayHours"].get("isClosed") or hr["holidayHours"].get("isRegularHours"):
                    continue
                hv = day_str(hr["holidayHours"])
                hd = date.fromisoformat(hr["date"])
                if hv == world.regular(eid, hd, snap):
                    continue
                k2 = world.cal_by.get((cc, hr["date"]), {}).get("day_key")
                w_ = 2 if cycle(hd) >= cycle(snap) - 1 else 1
                sp_c[hv] += w_
                if k2 in EVE_KEYS:
                    ev_c[hv] += w_
            habit_cache[ek] = (ev_c.most_common(1)[0] if ev_c else None, sp_c.most_common(1)[0] if sp_c else None)
        eve_m, sp_m = habit_cache[ek]
        f["eve_mode_n"] = eve_m[1] if eve_m else 0
        f["spec_mode_n"] = sp_m[1] if sp_m else 0
        if eve_m and key in EVE_KEYS:
            cands[eve_m[0]].add("eve_mode")
            if span(reg) and span(eve_m[0]):
                cands[fmt(span(reg)[0], span(eve_m[0])[1])].add("eve_close")
        if sp_m:
            cands[sp_m[0]].add("spec_mode")
        # peers
        pb = world.peer(eid, key)
        if pb:
            for k in ("share_no_exception_entered", "share_entered_closed", "share_entered_special_hours",
                      "share_entered_regular", "closed_share_among_entered"):
                f["peer_" + k] = float(pb[k]) if pb[k] else None
            if pb["median_open_special"] and pb["median_close_special"]:
                ph = f"{pb['median_open_special']}-{pb['median_close_special']}"
                cands[ph].add("peer")
                if span(reg):
                    cands[fmt(span(reg)[0], span(ph)[1])].add("peer_close")
                    cands[fmt(span(ph)[0], span(reg)[1])].add("peer_open")
        # owner profile
        if eid not in dil_cache:
            dil_cache[eid] = world.diligence(eid, snap)
            perm_cache[eid] = world.perm_closed_signal(eid, snap)
        f["n_entries"], f["n_own_entries"], f["median_lead"] = dil_cache[eid]
        hk = (eid, season)
        if hk not in habit_cache:
            hc = {"closed": 0, "special": 0, "regular": 0}
            for hr in world.hol_by_ent.get(eid, []):
                if hr["entered_at"] < snap.isoformat() and cycle(date.fromisoformat(hr["date"])) == cycle(snap) - 1:
                    hv = "REGULAR" if hr["holidayHours"].get("isRegularHours") else None
                    hv = hv or ("closed" if hr["holidayHours"].get("isClosed") else "special")
                    hc[{"REGULAR": "regular"}.get(hv, hv)] += 1
            habit_cache[hk] = hc
            habit_cache[(eid, season, "an")] = world.holiday_closure_profile(eid, snap, cc)
        f["hol_apv_mean"], f["hol_closed_share"] = habit_cache[(eid, season, "an")]
        hc = habit_cache[hk]
        tot = sum(hc.values())
        f["hab_n"] = tot
        f["hab_closed"] = hc["closed"] / tot if tot else None
        f["hab_special"] = hc["special"] / tot if tot else None
        f["perm_rev"], f["perm_sugg"] = perm_cache[eid]
        f["listed_closed"] = int(bool(e.get("closed")))
        f["has_now_entry"] = int(now_entry is not None)
        f["shown_closed"] = int(shown == "closed")
        f["reg_closed"] = int(reg == "closed")
        f["shown_is_reg"] = int(shown == reg)
        f["weekday"] = d.weekday()
        f["days_ahead"] = (d - snap).days
        f["country"], f["segment"], f["key"] = cc, e["c_segment"], key
        f["tier"] = world.tiers.get(e["address"]["city"], "town")
        f["day_type"] = r.get("day_type", "")
        f["customer_years"] = (snap - date.fromisoformat(e.get("c_connectCustomerSince", "2023-01-01"))).days / 365
        sp_shown, sp_reg = span(shown), span(reg)
        truth = lab.get((eid, r["date"]), {}).get("truth_hours")
        exp = lab.get((eid, r["date"]), {}).get("expected_action")
        for val, srcs in cands.items():
            c = dict(f)
            c.update({"entity_id": eid, "date": r["date"], "split": r["split"], "season": season,
                      "cand": val, "shown": shown, "reg": reg, "truth": truth, "expected": exp,
                      "y": int(truth == val) if truth is not None else None})
            for s in SOURCES:
                c["src_" + s] = int(s in srcs)
            c["n_src"] = len(srcs - {"shown", "closed", "reg", "reg_m60", "reg_p60", "reg_m120", "peer_close", "peer_open", "eve_close"})
            c["cand_closed"] = int(val == "closed")
            spc = span(val)
            c["cand_minutes"] = spc[2] if spc else 0
            c["cand_open_vs_reg"] = (spc[0] - sp_reg[0]) if spc and sp_reg else None
            c["cand_close_vs_reg"] = (spc[1] - sp_reg[1]) if spc and sp_reg else None
            c["cand_min_vs_shown"] = ((spc[2] if spc else 0) - (sp_shown[2] if sp_shown else 0))
            out.append(c)
    return pd.DataFrame(out)


if __name__ == "__main__":
    import time
    t = time.time()
    w = World()
    print("loaded", time.time() - t)
    W = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "work"); os.makedirs(W, exist_ok=True)
    for s in (2024, 2025, 2026):
        df = build(w, s)
        df.to_parquet(f"{W}/cands_{s}.parquet")
        print(s, len(df), df.groupby(["entity_id", "date"]).ngroups, "coverage(truth in cands)",
              df[df.truth.notna()].groupby(["entity_id", "date"]).y.max().mean(), time.time() - t)
