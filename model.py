"""Train the candidate ranker and produce predictions.

    python model.py eval      # train 2024+2025 (dev), score 2026 dev + 2025 back-test (trained on 2024+2026)
    python model.py predict   # train on all dev seasons, write predictions_2026.csv for every target row
"""
from __future__ import annotations

import csv
import importlib.util
import os
import sys

import lightgbm as lgb
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

W = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "work")
DATA_ROOT = os.environ.get("CONNECT_DATA", "/home/claude/src/Fonecta_SinceAI2026/data/FONECTA_CONNECT_SUGGESTS_2026")
spec = importlib.util.spec_from_file_location("evaluate", os.path.join(DATA_ROOT, "evaluation", "evaluate.py"))
EV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(EV)

CAT = ["country", "segment", "key", "tier", "day_type", "ly1_kind", "ly2_kind", "ly1_sugg_kind", "ly2_sugg_kind",
       "mall_kind", "pilot_decision", "sugg_now_status"]
DROP = {"entity_id", "date", "split", "season", "cand", "shown", "reg", "truth", "expected", "y"}


def load(seasons):
    df = pd.concat([pd.read_parquet(f"{W}/cands_{s}.parquet") for s in seasons], ignore_index=True)
    for c in CAT:
        if c not in df:
            df[c] = None
        df[c] = df[c].astype("category")
    return df


def feats(df):
    return [c for c in df.columns if c not in DROP]


def align(df, ref):
    for c in CAT:
        df[c] = pd.Categorical(df[c].astype(object), categories=ref[c].cat.categories)
    for c in feats(ref):
        if c not in df:
            df[c] = np.nan
    return df


def train(tr):
    tr = tr[tr.y.notna()]
    X = tr[feats(tr)]
    m = lgb.LGBMClassifier(n_estimators=600, learning_rate=0.03, num_leaves=63, min_child_samples=20,
                           subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1)
    m.fit(X, tr.y.astype(int), categorical_feature=[c for c in CAT if c in X])
    return m


def decide(df, p, thr=0.5, margin=0.0, flag_rule=True, thr_closed=None):
    thr_closed = thr if thr_closed is None else thr_closed
    df = df.assign(p=p)
    out = {}
    for (eid, d), g in df.groupby(["entity_id", "date"], sort=False):
        shown = g.shown.iloc[0]
        ps = g.loc[g.cand == shown, "p"].max()
        ns = g[g.cand != shown].sort_values("p", ascending=False)
        r = g.iloc[0]
        if flag_rule and r.listed_closed == 0 and (r.perm_rev >= 1 or r.perm_sugg >= 1):
            out[(eid, d)] = ("FLAG", "", 0.8, "CLOSED_SIGNALS")
            continue
        if len(ns):
            best = ns.iloc[0]
            t = thr_closed if best.cand == "closed" else thr
            if best.p >= t and best.p > ps + margin:
                srcs = [s[4:] for s in ns.columns if s.startswith("src_") and best[s] == 1]
                out[(eid, d)] = ("SUGGEST", best.cand, round(float(best.p), 3), "+".join(srcs))
                continue
        out[(eid, d)] = ("NO_ACTION", "", round(float(1 - (ns.p.max() if len(ns) else 0)), 3), "")
    return out


def score(preds, labels):
    P = {k: (a, EV.norm(h), c) for k, (a, h, c, _) in preds.items()}
    return EV.score(P, os.path.join(DATA_ROOT, "labels", labels))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "eval"
    if mode == "cv":
        from sklearn.model_selection import GroupKFold
        allx = load((2024, 2025, 2026))
        allx = allx[allx.split == "dev"]
        ents = allx.entity_id.values
        P = pd.Series(np.nan, index=allx.index)
        for k, (tri, tei) in enumerate(GroupKFold(5).split(allx, groups=ents)):
            tr = allx.iloc[tri]
            m = train(tr)
            P.iloc[tei] = m.predict_proba(allx.iloc[tei][feats(tr)])[:, 1]
        allx["p"] = P
        allx.to_parquet(f"{W}/cv_scored.parquet")
        for s_, lab in ((2026, "dev_labels_2026.csv"), (2025, "dev_labels_2025_backtest.csv")):
            te = allx[allx.season == s_]
            for thr, tc in ((0.4, 0.4), (0.45, 0.45), (0.45, 0.55), (0.5, 0.5), (0.4, 0.55), (0.35, 0.5)):
                res = score(decide(te, te.p.values, thr, thr_closed=tc), lab)
                print(s_, thr, tc, res["score_0_100"], "prec", res["precision_exact"], "rec", res["recall_exact"],
                      "harm", res["harmful_suggestions"], "views", res["search_views_protected_pct"])
        return
    if mode == "eval":
        for tr_s, te_s, lab in [((2024, 2025), 2026, "dev_labels_2026.csv"), ((2024, 2026), 2025, "dev_labels_2025_backtest.csv")]:
            tr = load(tr_s)
            if te_s == 2026:
                tr = tr[tr.split == "dev"]
            te = load([te_s])
            te = align(te[te.split == "dev"].copy(), tr)
            m = train(tr)
            p = m.predict_proba(te[feats(tr)])[:, 1]
            for thr in (0.35, 0.45, 0.55, 0.65):
                res = score(decide(te, p, thr), lab)
                print(te_s, thr, res["score_0_100"], "prec", res["precision_exact"], "rec", res["recall_exact"],
                      "harm", res["harmful_suggestions"], "views", res["search_views_protected_pct"], res["breakdown"])
            if te_s == 2026:
                imp = pd.Series(m.feature_importances_, feats(tr)).sort_values(ascending=False)
                print(imp.head(25))
    else:
        thr = float(sys.argv[2]) if len(sys.argv) > 2 else 0.4
        tr = load((2024, 2025, 2026))
        tr = tr[(tr.split == "dev") & tr.y.notna()]
        m = train(tr)
        te = align(load([2026]), tr)
        p = m.predict_proba(te[feats(tr)])[:, 1]
        from ev_decide import decide_ev
        preds = decide_ev(te, p, 1.0, 0.0, 0.8)
        te.assign(p=p).to_parquet(f"{W}/scored_2026.parquet")
        out = os.path.join(os.path.dirname(W), "predictions_2026.csv")
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["entity_id", "date", "action", "hours", "confidence"])
            for (eid, d), (a, h, c, b) in preds.items():  # noqa
                if a != "NO_ACTION":
                    w.writerow([eid, d, a, h, c])
        print("wrote", out, sum(1 for v in preds.values() if v[0] != "NO_ACTION"))
        m.booster_.save_model(f"{W}/ranker.txt")


if __name__ == "__main__":
    main()
