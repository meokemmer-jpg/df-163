# DF-163 LexVance-Wegzugssteuer-Risiko-Tracker [CRUX-MK]

**Status:** SKELETON-CONDITIONAL (Welle-51 W51-B Skeleton-Wave-2)
**Domain:** K_0 (LexVance Legal Revenue + Steuer-Risiko)
**Welle:** 25

## Mission

Per-Client-Wegzugssteuer-Deferral-Risk-Tracking. Tracking:
- Active-Deferrals-Count
- Total-Deferred-Tax-EUR
- High-Risk-Cases-Count
- Compliance-Deadline-Aging

**NIEMALS Steuer-Empfehlungen oder Legal-Advice produzieren.**

## Usage

```bash
cd ~/Projects/dark-factories/df-163
python df-163-engine.py        # Mock-Mode default
pytest tests/                   # Existing tests
```

## Output

- Reports: `reports/df-163-{date}.json`
- STOP-Flag: `/tmp/df-163.stop`

[CRUX-MK]
