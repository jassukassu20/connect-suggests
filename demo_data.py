"""Bundle everything the demo UI needs into one JSON (embedded in the static demo, served by connect_server)."""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import D  # noqa: E402

W = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "work")
STORY = {
    "FI-D0001": "Fonecta's own example – last year's exceptions exist, nothing entered this year",
    "FI-D0004": "Store in a shopping centre that already published holiday hours",
    "SE-D0008": "Swedish café – closed on julafton",
    "NO-D0009": "Norwegian bakery – pilot market",
    "FI-D0012": "Standing permission – apply first, then inform",
    "FI-D0017": "NEW customer – no history, no previous decisions",
    "SE-D0016": "Changed regular hours, never updated the listing",
    "FI-D0006": "Summer terrace that forgot its winter break",
    "FI-D0011": "Closed for good – flag to a human, don't suggest",
    "FI-D0013": "Already correct – stay quiet",
    "FI-D0003": "Florist – standing permission, longer pre-Christmas hours",
    "FI-D0007": "Hair salon closes between Christmas and New Year",
    "FI-D0010": "Pub next to the arena",
    "FI-D0002": "Restaurant closed on Sundays",
    "FI-D0005": "Ski rental in Levi",
    "FI-D0014": "Play centre, school holidays",
    "NO-D0015": "24/7 gym – nothing to change",
}


def main():
    cases = json.load(open(f"{W}/demo_cases.json"))
    queue = json.load(open(f"{W}/cases.json"))
    lst = defaultdict(list)
    for l in json.load(open(D("data", "listings.json")))["listings"]:
        if l["entityId"] in cases:
            lst[l["entityId"]].append({k: l[k] for k in ("publisherName", "status", "typicalUpdateSpeedSeconds")})
    modes = Counter(q["mode"] for q in queue)
    kpi = {
        "customers": len(queue), "messages": modes["SUGGEST"] + modes["ASK"], "auto": modes["AUTO_APPLY"],
        "flag": modes["FLAG"], "quiet": modes["QUIET"], "opted_out": modes["OPTED_OUT"],
        "suggestions": sum(q["n_items"] for q in queue),
        "views_at_risk": round(sum(q["views_at_risk"] for q in queue)),
        "health": sum(1 for q in queue if q["health"]),
        "by_country": dict(Counter(q["country"] for q in queue if q["mode"] in ("SUGGEST", "AUTO_APPLY"))),
        "model": {"baseline_dev": 54.5, "baseline_bt": 53.2, "cv_dev": 61.4, "cv_bt": 60.4,
                  "precision": 0.83, "recall": 0.71, "views_protected": 68.7, "views_protected_base": 57.2},
    }
    for eid, c in cases.items():
        c["story"] = STORY.get(eid)
        c["listings"] = sorted(lst.get(eid, []), key=lambda x: x["typicalUpdateSpeedSeconds"])
    out = {"kpi": kpi, "queue": queue[:400], "cases": cases,
           "demo_order": [k for k in STORY if k in cases] + [q["entity_id"] for q in queue[:25] if q["entity_id"] in cases and "-D" not in q["entity_id"]]}
    json.dump(out, open(f"{W}/demo_bundle.json", "w"), ensure_ascii=False)
    print(kpi, len(json.dumps(out)) // 1024, "KB")


if __name__ == "__main__":
    main()
