"""Stage 2: business-level coherence.

Stage-1 scores each (business, day) on its own. Owners are consistent across holidays (closed on Christmas Day →
very likely closed on Boxing Day too), so stage 2 adds, for every candidate, what stage 1 believes about the
same business's *other* days this season. Out-of-fold stage-1 scores are used for training, so nothing leaks.

    python stage2.py cv        # grouped CV of the 2-stage model
    python stage2.py predict   # final predictions_2026.csv
"""
from __future__ import annotations

import os
import sys

import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as M  # noqa: E402
from ev_decide import decide_ev  # noqa: E402

W = M.W


def add_context(df, pcol="p1"):
    """Business-level summaries of stage-1 beliefs, excluding the row's own day."""
    df = df.copy()
    g = df.groupby(["season", "entity_id", "date"], sort=False)
    row = pd.DataFrame({
        "p_closed": g.apply(lambda x: x.loc[x.cand == "closed", pcol].max(), include_groups=False),
        "p_shown": g.apply(lambda x: x.loc[x.cand == x.shown, pcol].max(), include_groups=False),
        "p_best_other": g.apply(lambda x: x.loc[x.cand != x.shown, pcol].max(), include_groups=False),
    }).reset_index()
    row["p_closed"] = row.p_closed.fillna(0)
    row["p_best_other"] = row.p_best_other.fillna(0)
    e = row.groupby(["season", "entity_id"])
    for c in ("p_closed", "p_shown", "p_best_other"):
        s, n = e[c].transform("sum"), e[c].transform("count")
        row[f"ent_{c}"] = (s - row[c]) / (n - 1).replace(0, np.nan)
    row["ent_n_change"] = e["p_best_other"].transform(lambda x: (x > 0.5).sum()) - (row.p_best_other > 0.5)
    df = df.merge(row, on=["season", "entity_id", "date"], how="left")
    df["p1_rank"] = df.groupby(["season", "entity_id", "date"])[pcol].rank(ascending=False)
    df["p1_gap_shown"] = df[pcol] - df.p_shown
    return df


def train2(tr, feats):
    m = lgb.LGBMClassifier(n_estimators=500, learning_rate=0.03, num_leaves=31, min_child_samples=40,
                           subsample=0.8, subsample_freq=1, colsample_bytree=0.7, verbose=-1, random_state=1)
    m.fit(tr[feats], tr.y.astype(int), categorical_feature=[c for c in M.CAT if c in feats])
    return m


def bag_train(tr, seeds=(0, 1, 2)):
    ms = []
    for s in seeds:
        X = tr[M.feats(tr)]
        m = lgb.LGBMClassifier(n_estimators=700, learning_rate=0.03, num_leaves=63, min_child_samples=20,
                               subsample=0.8, subsample_freq=1, colsample_bytree=0.7, verbose=-1, random_state=s)
        m.fit(X, tr.y.astype(int), categorical_feature=[c for c in M.CAT if c in X])
        ms.append(m)
    return ms


def bag_pred(ms, X):
    return np.mean([m.predict_proba(X)[:, 1] for m in ms], axis=0)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "cv"
    from sklearn.model_selection import GroupKFold
    allx = M.load((2024, 2025, 2026))
    dev = allx[(allx.split == "dev") & allx.y.notna()].reset_index(drop=True)
    folds = list(GroupKFold(5).split(dev, groups=dev.entity_id.values))
    # stage 1 out-of-fold (bagged)
    f1 = M.feats(dev)
    p1 = np.full(len(dev), np.nan)
    for tri, tei in folds:
        ms = bag_train(dev.iloc[tri])
        p1[tei] = bag_pred(ms, dev.iloc[tei][f1])
    dev["p1"] = p1
    dev = add_context(dev)
    f2 = M.feats(dev.drop(columns=["p1"])) + ["p1", "p_closed", "p_shown", "p_best_other", "ent_p_closed", "ent_p_shown",
                                              "ent_p_best_other", "ent_n_change", "p1_rank", "p1_gap_shown"]
    f2 = list(dict.fromkeys(f for f in f2 if f in dev))
    if mode == "cv":
        dev["p2"] = np.nan
        for tri, tei in folds:   # same folds → stage-2 never sees the test businesses
            m2 = train2(dev.iloc[tri], f2)
            dev.loc[dev.index[tei], "p2"] = m2.predict_proba(dev.iloc[tei][f2])[:, 1]
        dev.to_parquet(f"{W}/cv2_scored.parquet")
        for s, lab in ((2026, "dev_labels_2026.csv"), (2025, "dev_labels_2025_backtest.csv")):
            te = dev[dev.season == s]
            for col in ("p1", "p2"):
                for mg in (0.0, 0.05, 0.1):
                    r = M.score(decide_ev(te, te[col].values, 1.0, mg, 0.8), lab)
                    print(s, col, mg, r["score_0_100"], r["precision_exact"], r["recall_exact"], r["harmful_suggestions"],
                          r["search_views_protected_pct"], flush=True)
    else:
        mg = float(sys.argv[2]) if len(sys.argv) > 2 else 0.05
        ms = bag_train(dev[list(dict.fromkeys(f1 + ["y"]))])
        te = M.align(M.load([2026]), dev)
        te["p1"] = bag_pred(ms, te[f1])
        te = add_context(te)
        m2 = train2(dev, f2)
        te["p"] = m2.predict_proba(te[f2])[:, 1]
        te.to_parquet(f"{W}/scored_2026.parquet")
        preds = decide_ev(te, te.p.values, 1.0, mg, 0.8)
        out = os.path.join(os.path.dirname(W), "predictions_2026.csv")
        import csv
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["entity_id", "date", "action", "hours", "confidence"])
            for (eid, d), (a, h, c, _) in preds.items():
                if a != "NO_ACTION":
                    w.writerow([eid, d, a, h, c])
        print("wrote", out)


if __name__ == "__main__":
    main()
