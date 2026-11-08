"""Second stage: learn expected scorer points of suggesting each candidate, from out-of-fold ranker probabilities
plus context. Suggest argmax if predicted points > threshold, else NO_ACTION."""
import os
import sys

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

sys.argv = ["x"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as M  # noqa: E402
from ev_decide import pts  # noqa: E402

allx = M.load((2024, 2025, 2026))
allx = allx[(allx.split == "dev") & allx.y.notna()].reset_index(drop=True)
allx["p"] = np.load(f"{M.W}/exp_bin_base.npy")
g = allx.groupby(["season", "entity_id", "date"], sort=False)
allx["gid"] = g.ngroup()
allx["p_rank"] = g.p.rank(ascending=False, method="first")
allx["p_max"] = g.p.transform("max")
allx["p_sum"] = g.p.transform("sum")
allx["p_shown"] = allx.p.where(allx.cand == allx.shown).groupby(allx.gid).transform("max").fillna(0)
allx["p_rel"] = allx.p / (allx.p_max + 1e-6)
allx["p_minus_shown"] = allx.p - allx.p_shown
allx["n_cands"] = g.p.transform("size")
X = allx[allx.cand != allx.shown].copy()
X["target"] = [pts(c, t, s) for c, t, s in zip(X.cand, X.truth, X.shown)]
X = X[X.p_rank <= 4]
F = M.feats(allx) + ["p_rank", "p_max", "p_sum", "p_shown", "p_rel", "p_minus_shown", "n_cands"]
F = [f for f in dict.fromkeys(F) if f not in ("gid",)]
CATS = [c for c in M.CAT if c in F]
X["pred"] = np.nan
for tri, tei in GroupKFold(5).split(X, groups=X.entity_id.values):
    m = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.03, num_leaves=31, min_child_samples=40, subsample=0.8,
                          subsample_freq=1, colsample_bytree=0.8, verbose=-1)
    m.fit(X.iloc[tri][F], X.iloc[tri].target, categorical_feature=CATS)
    X.iloc[tei, X.columns.get_loc("pred")] = m.predict(X.iloc[tei][F])


def decide(df, thr):
    out = {}
    best = df.sort_values("pred", ascending=False).drop_duplicates(["entity_id", "date"])
    for r in best.itertuples():
        if r.listed_closed == 0 and (r.perm_rev >= 1 or r.perm_sugg >= 1):
            out[(r.entity_id, r.date)] = ("FLAG", "", 0.8, "")
        elif r.pred > thr:
            out[(r.entity_id, r.date)] = ("SUGGEST", r.cand, round(float(min(1, max(0, r.p))), 3), "")
    return out


for s, lab in ((2026, "dev_labels_2026.csv"), (2025, "dev_labels_2025_backtest.csv")):
    te = X[X.season == s]
    for thr in (-0.05, 0.0, 0.05, 0.1, 0.15):
        r = M.score(decide(te, thr), lab)
        print(s, thr, r["score_0_100"], r["precision_exact"], r["recall_exact"], r["harmful_suggestions"], r["search_views_protected_pct"], flush=True)
X[["season", "entity_id", "date", "cand", "pred"]].to_parquet(f"{M.W}/stack_oof.parquet")
