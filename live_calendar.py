"""Bonus: rebuild the public-holiday part of calendar_special_days.csv from a live source (python-holidays, MIT)
and diff it against the dataset file.    python live/live_calendar.py"""
import csv, os, holidays
DATA = os.environ.get("CONNECT_DATA", "/home/claude/src/Fonecta_SinceAI2026/data/FONECTA_CONNECT_SUGGESTS_2026")
rows = list(csv.DictReader(open(os.path.join(DATA, "data", "calendar_special_days.csv"), encoding="utf-8")))
out = []
for c in ("FI", "SE", "NO"):
    live = {d.isoformat(): n for y in (2024, 2025, 2026, 2027) for d, n in holidays.country_holidays(c, years=y).items()}
    file_days = {r["date"]: r for r in rows if r["country"] == c}
    flag = {r["date"] for r in rows if r["country"] == c and r["official_public_holiday"].lower() in ("true", "1", "yes")}
    missing = sorted(d for d in live if d not in file_days)
    not_flag = sorted(d for d in live if d in file_days and d not in flag)
    only_file = len([d for d in file_days if d not in live])
    print(f"{c}: live public holidays {len(live)} | in file {len(live) - len(missing)} | missing from file {missing} "
          f"| flag mismatch {len(not_flag)} | file-only days (eves, commercial, Lucia, Father's Day…) {only_file}")
    for d, n in live.items():
        out.append({"country": c, "date": d, "name_local": n})
with open(os.path.join(os.path.dirname(__file__), "live_public_holidays.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["country", "date", "name_local"]); w.writeheader(); w.writerows(out)
