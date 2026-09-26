# Test catalogue

Seed data for the clinical catalogue tables (see [docs/04-data-design.md](../../docs/04-data-design.md)). Load it with:

```bash
docker compose exec api python -m app.cli seed-catalogue
```

The loader is idempotent. Re-running it updates tests by `code` and replaces their units, ranges and limits.

| File | Rows | Notes |
|---|---|---|
| `organ_systems.csv` | 10 | Organ systems that drive the 3D body colouring. `mesh_ids` are placeholders until the anatomy GLB exists (Sprint 6). **Hindi and Odia names are drafts** awaiting the native-speaker review (task T2.5). |
| `lab_tests.csv` | 70 | LOINC code, canonical unit, display precision, plausible bounds (sanity checks, **not** reference ranges), biological variation and the spellings seen on Indian reports (`aliases`, `\|`-separated). |
| `unit_conversions.csv` | 50 | Factor and offset from a *normalised* unit key to the canonical unit: `canonical = value × factor + offset`. Unit spellings are normalised by `app/catalogue/units.py`. |
| `reference_ranges.csv` | 82 | Typical adult intervals, used **only** when a report prints no range (`ref_source = catalogue`). The lab's printed range always wins. |
| `critical_limits.csv` | 14 | Commonly published adult critical limits. |

## Caveats (read before relying on the numbers)

- **Critical limits are a draft.** They must be reviewed and signed off by the project's clinical advisor before M3 (`critical_limit.reviewed_by`, `reviewed_at`). Until then the loader records them as unreviewed.
- **Biological-variation values (`cv_i`, `cv_a`) are approximate** and cover 36 tests. Verify each against the EFLM Biological Variation Database before Sprint 4 relies on them for reference-change values. Tests with blank values get no change-significance flag.
- **Reference ranges are educational defaults** for adults and vary between labs, methods and populations.
- **LOINC codes** are checked for a valid check digit by the test suite. That catches typos, not wrong-but-valid codes. Spot-check against loinc.org when editing.
- Qualitative urine dipstick results (protein, glucose and ketones reported as Nil / Trace / +) are not in this catalogue yet.
