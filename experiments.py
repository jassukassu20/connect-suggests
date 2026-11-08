"""Grouped-CV experiments: params, lambdarank, seed ensembles. Prints scores with the EV decision."""
import sys

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

sys.argv = ["x"]
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as M  # noqa: E402
from ev_decide import decide_ev  # noqa: E402

allx = M.load((2024, 2025, 2026))
allx = allx[(allx.split == "dev") & allx.y.notna()].reset_index(drop=True)
F = M.feats(allx)
CATS = [c for c in M.CAT if c in F]
allx["gid"] = allx.groupby(["season", "entity_id", "date"], sort=False).ngroup()
folds = list(GroupKFold(5).split(allx, groups=allx.entity_id.values))


def softmax_by_group(s, g):
    s = pd.Series(s)
    e = np.exp(s - s.groupby(g).transform("max"))
    return (e / e.groupby(g).transform("sum")).values


def run(name, fit_pred):
    P = np.zeros(len(allx))
    for tri, tei in folds:
        P[tei] = fit_pred(allx.iloc[tri], allx.iloc[tei])
    np.save(f"{M.W}/exp_{name}.npy", P)
    res = []
    for s, lab in ((2026, "dev_labels_2026.csv"), (2025, "dev_labels_2025_backtest.csv")):
        m = (allx.season == s).values
        te = allx[m]
        best = max((M.score(decide_ev(te, P[m], 1.0, mg, 0.8), lab)["score_0_100"], mg) for mg in (0.0, 0.05, 0.1))
        res.append(best)
    print(name, res, flush=True)
    return P


def binary(params, seeds=(0,)):
    def f(tr, te):
        out = 0
        for sd in seeds:
            m = lgb.LGBMClassifier(**params, random_state=sd, verbose=-1)
            m.fit(tr[F], tr.y.astype(int), categorical_feature=CATS)
            out = out + m.predict_proba(te[F])[:, 1]
        return out / len(seeds)
    return f


def rank(params, seeds=(0,)):
    def f(tr, te):
        tr = tr.sort_values("gid")
        grp = tr.groupby("gid", sort=False).size().values
        out = 0
        for sd in seeds:
            m = lgb.LGBMRanker(**params, random_state=sd, verbose=-1)
            m.fit(tr[F], tr.y.astype(int), group=grp, categorical_feature=CATS)
            out = out + m.predict(te[F])
        s = out / len(seeds)
        return softmax_by_group(s, te.gid.values)
    return f


base = dict(n_estimators=600, learning_rate=0.03, num_leaves=63, min_child_samples=20, subsample=0.8, subsample_freq=1, colsample_bytree=0.8)
which = sys.argv_exp if hasattr(sys, "argv_exp") else None
P1 = run("bin_base", binary(base))
P2 = run("bin_big", binary(dict(base, n_estimators=1500, learning_rate=0.02, num_leaves=127, min_child_samples=40, reg_lambda=2.0)))
P3 = run("rank", rank(dict(objective="lambdarank", n_estimators=800, learning_rate=0.03, num_leaves=63, min_child_samples=20,
                          subsample=0.8, subsample_freq=1, colsample_bytree=0.8)))
P4 = run("rank_xendcg", rank(dict(objective="rank_xendcg", n_estimators=800, learning_rate=0.03, num_leaves=63, min_child_samples=20,
                                 subsample=0.8, subsample_freq=1, colsample_bytree=0.8)))
for nm, P in (("ens_bin_rank", (P2 + P3) / 2), ("ens_all", (P1 + P2 + P3 + P4) / 4), ("ens_bin2_rank2", (P2 + P4) / 2)):
    res = []
    for s, lab in ((2026, "dev_labels_2026.csv"), (2025, "dev_labels_2025_backtest.csv")):
        m = (allx.season == s).values
        res.append(max((M.score(decide_ev(allx[m], P[m], 1.0, mg, 0.8), lab)["score_0_100"], mg) for mg in (0.0, 0.05, 0.1)))
    print(nm, res, flush=True)
