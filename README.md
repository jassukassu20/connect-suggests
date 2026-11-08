# Connect Suggests – Customer Approves

**Since AI Hackathon 2026 × Fonecta.** Connect watches every customer's listing, notices *before* a holiday when Google is about to show the wrong hours, proposes the right hours with a reason the owner understands at a glance, and lets the owner approve, edit or decline from their phone in one tap. No login. Then it writes the approved change to Yext and confirms where the new hours now show.

> All data is synthetic (the Since AI simulator v1.1). Nothing real is used.

## Results (dev split, honest validation)

| | Score /100 | Exact precision | Recall | Harmful | Search views protected |
|---|---|---|---|---|---|
| Baseline (copy last year → mall → peers) | 54.5 | 0.90 | 0.59 | 224 | 57.2 % |
| **Our ranker, 2026 season** (5-fold, grouped by business) | **61.4** | 0.83 | 0.71 | 457 | **68.7 %** |
| **Our ranker, 2025 back-test** (5-fold, grouped by business) | **60.4** | 0.83 | 0.70 | 504 | 65.9 % |

* The cross-validation keeps every business entirely in train *or* test, so the model cannot memorise a business. The organisers' hidden test businesses work the same way, so this is the number to expect.
* `predictions_2026.csv` (repo root) covers every target row. The final model is trained on all dev seasons. Run against the dev labels it scores 72.7, but that is in-sample, so don't quote it.
* Season-wide plan: **2,758 owners to contact, 15,933 date suggestions, 56 auto-applied under standing permission, 12 flagged to a human, 185 left alone, 6 opted out**, covering ~247k search views at risk.

## Demo video
`connect_suggests_pitch.mp4` (2 min 15 s, 1080p) has an English voice-over and burned-in English subtitles. A version without burned-in subtitles plus a separate `.srt` file are included. It follows problem → solution → live demo → business impact. Everything shown runs in the prototype on Fonecta's simulated challenge data. The voice is AI-generated (Kokoro TTS). Rebuild it with `python video/narration.py && python video/film.py && python video/assemble.py`.

## Run it

```bash
pip install pandas pyarrow lightgbm scikit-learn        # MIT / BSD / Apache-2.0
export CONNECT_DATA=/path/to/FONECTA_CONNECT_SUGGESTS_2026
python engine/build.py          # candidates + features for seasons 2024, 2025, 2026  (~20 s)
python engine/model.py cv       # honest grouped cross-validation
python engine/model.py predict  # train on all dev seasons → predictions_2026.csv
python engine/suggest.py        # one case per business: items, evidence, priority, messages
python engine/demo_data.py      # bundle for the UI
python connect_server.py        # demo UI + Yext mock → http://localhost:8800 (step 5 does a real PUT)

# Real Yext sandbox write path (keys never committed):
YEXT_BASE_URL=https://sbx-api.yextapis.com YEXT_API_KEY=*** SANDBOX_ENTITY_ID=<test entity> python connect_server.py
```
`app/connect_story.html` is the pitch demo: a guided, story-by-story app (six stories, owner's phone, no code on screen). `app/connect_demo.html` is the operator console with the whole queue. It runs the full loop in the browser and shows the exact Yext request.

## The five steps

1. **Detect.** For each of 41,755 business×special-day rows we build every candidate the data supports: the hours shown now, closed, regular hours, last year's and the year before's exception (also re-applied relative to this year's weekday hours), the shopping centre's published hours, peer medians, Google user edits, the 2025 pilot outcome, sibling days, shifted variants, and the owner's habitual eve hours. Owners reuse the same short hours on 77 % of eve-type days (23 Dec, Christmas Eve, the days between, New Year's Eve, Epiphany Eve), so hours entered on one eve predict the others. That raised the share of rows whose truth is among the candidates from 93 % to 96 %. A LightGBM ranker scores how likely each candidate is the truth (~60 features). If the best candidate beats "what Google shows" with enough confidence, the date is wrong.
2. **Suggest.** An expected-value rule (`engine/ev_decide.py`) turns the ranker's probabilities into the action with the most expected points under the scorer: a wrong closed/open flip costs −1, so "closed" needs more certainty. Each date keeps all of its evidence, and the strongest supporting piece becomes the reason in the message. Dates are ranked by *confidence × expected search views*, and a closure gets 1.5× weight because that is the closed-door risk.
3. **Contact.** One bundled message per business in the owner's language (fi/sv/nb/en) on their preferred channel (SMS, WhatsApp, email, app push), sent inside their contact window. Opt-outs get nothing. Standing permission means apply first, then inform. When the model isn't confident on a big holiday for an owner with no history, we **ask** an open question instead of guessing.
4. **Decide (no login).** Reply `KYLLÄ / JA / YES` to approve everything, or open the one-time link to approve, edit (time picker or "closed") or decline each date. A checkbox grants standing permission: *"Handle public holidays like this from now on"*.
5. **Apply + confirm.** Read-modify-write `PUT /v2/accounts/me/entities/{id}` with the full `hours` object (validated like Yext), then `GET listings` → *"Done! Your new hours now show on Google ~2 min, Hitta.se ~10 min, Bing ~1 d…"*. Each write is logged to `work/audit.jsonl` with old value, new value, basis, confidence and decision.

**Learning.** An edit is stored as the owner's own answer for that holiday and beats the model next season. A decline suppresses that holiday for the business (and is a negative signal for that basis). Repeated accepts make the owner eligible for standing permission. The pilot log's past decisions are already features (`pilot_decision`, `pilot_rejected`). In the demo, use *Preview next season* to see this.

**Guardrails.** Nothing is published without approval or standing permission. Standing permission covers only confident repeat patterns (≥0.8 and own history or the mall). Businesses that look closed for good are **flagged, never messaged**. Opt-outs are respected. Every sentence in a message is backed by evidence (deterministic templates, no invented facts).

## Data sources that mattered most

| Signal | How we used it | Where Connect gets it in production |
|---|---|---|
| Exception-hour history (own, last 2 seasons) | Strongest candidate, also re-applied relative to this year's weekday hours | Connect audit log / Yext `holidayHours` history |
| **Analytics: customer actions per search view** | On days a business was really closed while Google said open, actions per view fall to about half (0.067 vs 0.149). Measured against the same weekday ±1–2 weeks, it reveals last year's real closures *even when the owner entered nothing*. This is the key signal for the 40 % with no history. | Yext Analytics Reports (`GOOGLE_CUSTOMER_ACTIONS`, `GOOGLE_SEARCH_VIEWS`) |
| Shopping-centre published hours | A store follows its centre (we learn whether it did last year) | Centre entities in Yext / centre websites |
| Peer benchmarks (type × country × city size) | Closed share and median special hours, the fallback for new customers | Connect's own aggregated customer data |
| Complaint reviews + Google user edits + pilot decisions | "Closed although Google said open" after a past holiday, edits for that date, last year's accept/edit | Yext Reviews, Publisher Suggestions, Connect suggestion log |

Listing health (beyond the score): reviews such as *"Numera öppet bara mån–lör 11–22"* trigger a regular-hours update (SE-D0016). *"Kesäravintola on tauolla"* triggers a seasonal-break suggestion (FI-D0006). Reviews or edits saying "closed for good" trigger FLAG (FI-D0011).

## What we tried that didn't work
- **Raw analytics ratios against the business's global average** were noise, because holiday seasonality swamps them. Local weekday normalisation (±7/±14 days) fixed that.
- **Phone-call spikes** looked promising in the brief, but they barely separate closed from open days (AUC ≈ 0.48).
- **Validating on the same businesses across seasons** gave 64 points, which is inflated by memorising businesses. We switched to entity-grouped CV (61.4).
- **One threshold for all candidates** produced too many harmful closed/open flips. Separate thresholds for "closed" cut harmful suggestions by ~25 % at equal score.
- Weather/events added little for the scored day types in this window. They are left for the ski-rental and arena-night stories.

- **Ensembles and a second-stage "expected points" model** (binary + LambdaRank + XE-NDCG, stacking) did not beat a single binary ranker with the expected-value rule. Gains were within ±0.3 points, so we kept the simple model. The remaining gap is information that isn't in the data, which is why the owner approves.

## Customer with no history (FI-D0017 Kahvila Kipinä)
New customer since Oct 2026: no exceptions, no decisions. Connect uses analytics from last season (customers acted as if the café was closed on Christmas Eve and New Year's Day) and peers (86 % of similar cafés close on Christmas Day). It suggests 3 confident closures and nothing else. For lower-confidence big holidays (Christmas Eve, Epiphany) it asks: *"Oletteko auki 24.12. (Jouluaatto)? Vastaa 1 = tavalliset ajat, 2 = kiinni, 3 = muu aika"*. Each answer becomes history for next year.

## Final customer messages
See **[MESSAGES.md](MESSAGES.md)**: Finnish, Swedish, Norwegian and English suggestions, standing-permission inform, ask, regular-hours and seasonal-break messages, and approve / edit / decline follow-ups.

## Bonus: live source
`live/live_calendar.py` rebuilds the public holidays from the **python-holidays** package (MIT) and diffs them against `calendar_special_days.csv`:
- **Quality:** 100 % agreement on every public holiday both cover (FI 47, SE 41, NO 37 days), and the official flags match.
- **Coverage:** the live source extends into 2027 (Easter, May Day and Midsummer 2027 are missing from the file), so Connect can plan the spring season now.
- **Gaps:** the live source has **none** of the days that cause the most wrong listings: Christmas Eve in SE/NO, 23 Dec, New Year's Eve, Black Friday, Lucia, Father's Day, the days between the holidays. That is 33–49 days per country. Connect needs its own curated layer of eves and commercial days on top of any holiday API.

## Third-party code, data and licences
| Component | Licence |
|---|---|
| Since AI dataset, mock API, yext_client | Code MIT, data CC BY 4.0 |
| LightGBM | MIT |
| pandas, NumPy, scikit-learn | BSD-3-Clause |
| pyarrow | Apache-2.0 |
| python-holidays | MIT |
| Inter, JetBrains Mono, Space Grotesk (Google Fonts) | SIL OFL 1.1 |
| Kokoro-82M voice model (video voice-over) / kokoro-onnx | Apache-2.0 / MIT |
| Playwright (video recording), FFmpeg (encoding) | Apache-2.0 / LGPL-2.1 (used as an external tool, not bundled) |

No GPL/AGPL components.
