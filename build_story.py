import json, os
H = os.path.dirname(os.path.abspath(__file__))
b = json.load(open(os.path.join(H, "..", "work", "demo_bundle.json")))
keep = ["FI-D0001", "FI-D0017", "FI-D0004", "NO-D0009", "FI-D0012", "FI-D0011"]
d = {"kpi": b["kpi"], "cases": {k: b["cases"][k] for k in keep}}
t = open(os.path.join(H, "story_template.html"), encoding="utf-8").read()
open(os.path.join(H, "connect_story.html"), "w", encoding="utf-8").write(t.replace("/*__DATA__*/null", json.dumps(d, ensure_ascii=False).replace("</", "<\\/")))
print("ok", os.path.getsize(os.path.join(H, "connect_story.html")) // 1024, "KB")
