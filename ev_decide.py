"""Expected-value decision: pick the action that maximises the scorer's expected points, using the ranker's
probabilities over all candidates as the belief about the truth."""
from __future__ import annotations

import numpy as np

from features import span


def near(a, b):
    sa, sb = span(a), span(b)
    if not sa or not sb:
        return False
    return abs(sa[0] - sb[0]) <= 30 and abs(sa[1] - sb[1]) <= 30


def pts(c, t, shown):
    """Scorer points for suggesting c if truth is t."""
    if t == shown:          # no change needed
        if c == shown:
            return -0.1
        return -1.0 if (c == "closed") != (shown == "closed") else -0.5
    if c == t:
        return 1.0
    if (c == "closed") != (t == "closed"):
        return -1.0
    return 0.6 if near(c, t) else 0.2


def decide_ev(df, p, power=1.0, margin=0.0, other_open=0.6, flag_rule=True):
    df = df.assign(p=np.asarray(p) ** power)
    out = {}
    for (eid, d), g in df.groupby(["entity_id", "date"], sort=False):
        r = g.iloc[0]
        shown = r.shown
        if flag_rule and r.listed_closed == 0 and (r.perm_rev >= 1 or r.perm_sugg >= 1):
            out[(eid, d)] = ("FLAG", "", 0.8, "CLOSED_SIGNALS")
            continue
        cands = list(g.cand)
        pr = g.p.values
        s = pr.sum()
        q = pr / max(1.0, s)
        other = max(0.0, 1 - q.sum())
        best, bev = None, margin
        for c in cands:
            if c == shown:
                continue
            ev = sum(qi * pts(c, t, shown) for t, qi in zip(cands, q))
            # residual mass: truth not among candidates (mostly open with other hours)
            ev += other * (other_open * (-1.0 if c == "closed" else 0.2) + (1 - other_open) * (1.0 if False else (-1.0 if c != "closed" else 0.0)))
            if ev > bev:
                best, bev = c, ev
        if best is None:
            out[(eid, d)] = ("NO_ACTION", "", 0.5, "")
        else:
            pc = float(g.loc[g.cand == best, "p"].max())
            out[(eid, d)] = ("SUGGEST", best, round(min(1.0, pc), 3), "")
    return out
