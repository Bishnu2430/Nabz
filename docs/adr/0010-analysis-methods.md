# ADR-0010 · How Nabz judges change and trends

**Status:** Accepted · 2026-09-28 · refines the change detector and trend analyser in [03 §8](../03-system-architecture.md#8-ai-and-data-science-components)

## Context

Sprint 4 turns confirmed values into statements a person reads: "higher than last time", "rising for three years", "would reach the upper limit around 2028". Two kinds of error matter:

- **A missed trend:** Nabz stays quiet about a real change.
- **A false alarm:** Nabz says "rising" about normal variation.

For a patient-facing app a false alarm costs more: it causes worry and erodes trust. Personal histories are also short, typically 3–6 reports over a few years, so methods that need many points don't apply.

## Decision

1. **Change since the previous result: the log-normal, asymmetric reference change value** (Fokkema et al., 2006), using each test's within-subject (CVi) and analytical (CVa) variation from the catalogue.
   - A change is "more than normal variation" only beyond the RCV at 95 %.
   - A rise needs to be slightly larger than a fall. The symmetric textbook RCV slightly understates rises and overstates falls for positive values.
2. **Trend: Theil–Sen slope with Sen's 90 % interval, and an exact Mann–Kendall test.**
   - The median of pairwise slopes ignores one odd result.
   - The exact null distribution (Mahonian numbers) is correct at n = 3–10, where normal approximations aren't.
3. **A trend is confirmed only when all of these hold:**
   - Mann–Kendall p < 0.10.
   - The results span at least 180 days.
   - The fitted change across the span exceeds the test's RCV.

   Consequences of the rule:
   - Three results can never confirm a trend (the smallest possible p is 1/3). The app says a fourth result will tell.
   - Tests without biological-variation data are never confirmed; their direction is shown only.
4. **Projection only for confirmed trends,** at most five years ahead, phrased as arithmetic on past results ("if this continues … it isn't a prediction").
5. **As-of analysis, recomputed per person.** Each result's analysis uses only results up to its own date. Adding or deleting a report recomputes the person's affected tests from scratch, so an older report uploaded late corrects the later ones.
6. **Population percentiles come from NHANES 2017–March 2020**, survey-weighted and always labelled as a US population. Indian population percentiles are not publicly available ([09 §2](../09-data-sources-and-licensing.md)).

## Alternatives considered

- **Least-squares slope with a t-test.** One outlier (a lab error, an acute illness) swings it, and it assumes normal residuals; neither holds for short personal series.
- **Bootstrap interval for the slope** (named in the first draft of doc 03). It is unreliable with 3–6 points; Sen's interval is exact under its assumptions.
- **Mann–Kendall alone.** It would call trends in tests without variation data. In synthetic histories about 1 in 12 noisy four-point series rise monotonically by chance.
- **Symmetric RCV.** It is simpler but biased for positive, skewed values.

## Consequences

Measured on 50 synthetic people with a planted yearly drift ([11 §11](../11-test-and-evaluation-plan.md#11-sprint-4-analysis-results)):

| Visits | Planted trend confirmed | False alarms on other tests |
|---|---|---|
| 3 | 0 % (by design) | 0 % |
| 4 | 72 % | 1.1 % |
| 5 | 88 % | 1.0 % |

- On stable primary tests, single-step changes were flagged 3.7 % of the time, inside the 5 % the RCV is designed for.
- The CVi and CVa values in the catalogue are approximate until each is checked against the EFLM database (catalogue README); the RCV inherits their accuracy.
- The critical limits used for FR-17 are a draft until the clinical advisor signs them off.
