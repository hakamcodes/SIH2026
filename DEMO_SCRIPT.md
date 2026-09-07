# Demo Script (backend-only)

Backend vertical slice, no frontend. Every command below is real -- copy/paste
and run it; nothing here is aspirational. See `LEGAL_DISCLAIMERS.md` for the
sitewide advisory disclaimer this system carries on every report and, once
built, every page.

Setup, once per session:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = "1"
cd backend
```

Reset to a clean database for a repeatable run:

```powershell
Remove-Item ..\data\lmd.db -ErrorAction SilentlyContinue
```

---

## Beat 1 -- Point-in-time law, no photo needed

The rule engine evaluates against whichever version of the law was in force
on the scan date. `LM-M04b` (Unit Sale Price declaration for non-standard
pack sizes) only exists in law from 2022-04-01.

```powershell
python -m lmd.cli evaluate --case TC-002 --as-of 2022-03-31
python -m lmd.cli evaluate --case TC-002 --as-of 2022-04-02
```

Compare `rule_results.LM-M04b.status` between the two runs: `NOT_IN_FORCE`
before the date, evaluated after it. This is the strongest single claim in
the build -- "which version of the law applied on this date" is answered
from data (`effective_from`/`effective_to` in
`packages/rules/lmd_rules.v1.json`), never a hardcoded branch.

## Beat 2 -- A real photograph, per-rule reasoning

```powershell
python -m lmd.cli scan ..\research\mainResearch\02_flat_box_clean.jpg --json
```

Read `rule_results`. `LM-C03` (manufacturer name and address, Rule 6(1)(a))
now passes from a genuinely parsed `Mfd. by ... Mumbai-400076` declaration --
not a synthetic fixture. `LM-C05` (manufacturing date, Rule 6(1)(d)) still
fails: the date on this package is a dot-matrix stamp, which classical OCR
does not reliably read. That failure is a fact about the photograph, not a
parser bug -- see `/api/v1/limitations`.

## Beat 3 -- The honest failure case

```powershell
python -m lmd.cli scan ..\research\mainResearch\04_rotated_blurry_dotmatrix.jpg --json
```

Expect `NEEDS_REVIEW` or `NON_COMPLIANT`, never `COMPLIANT` -- measured zero
text recovery on this image is an encoded expectation in
`tests/test_golden_images.py`, not a surprise.

## Beat 4 -- Rules are data, hot-swappable at runtime

```powershell
uvicorn lmd.main:app --reload --port 8000
```

In another shell:

```powershell
curl http://localhost:8000/api/v1/rules
$env:LMD_RULES_PATH = (Resolve-Path ..\packages\rules\lmd_rules.v2.draft.json)
curl -Method POST http://localhost:8000/api/v1/rules/reload -Headers @{ Authorization = "Bearer $env:LMD_INSPECTOR_API_TOKEN"; "X-Inspector-Id" = "demo-inspector" }
curl http://localhost:8000/api/v1/rules
```

`rule_count` changes and the new `LM-F10` (DIAGNOSTIC demo rule) appears --
no code was redeployed, only a JSON file swap.

## Beat 5 -- The reason-to-believe gate is a hard gate

```powershell
$scan = curl -Method POST http://localhost:8000/api/v1/scans -Form @{ image = Get-Item ..\research\mainResearch\02_flat_box_clean.jpg } | ConvertFrom-Json
$case = curl -Method POST http://localhost:8000/api/v1/cases -Headers @{ Authorization = "Bearer $env:LMD_INSPECTOR_API_TOKEN"; "X-Inspector-Id" = "demo-inspector" } -Body (@{ scan_id = $scan.scan_id } | ConvertTo-Json) -ContentType "application/json" | ConvertFrom-Json

# Attempt to advance without a reason-to-believe note -- expect HTTP 422
curl -Method PUT "http://localhost:8000/api/v1/cases/$($case.case_id)" -Headers @{ Authorization = "Bearer $env:LMD_INSPECTOR_API_TOKEN"; "X-Inspector-Id" = "demo-inspector" } -Body (@{ status = "CONFIRMED_VIOLATION" } | ConvertTo-Json) -ContentType "application/json"

# Now with the note -- succeeds
curl -Method PUT "http://localhost:8000/api/v1/cases/$($case.case_id)" -Headers @{ Authorization = "Bearer $env:LMD_INSPECTOR_API_TOKEN"; "X-Inspector-Id" = "demo-inspector" } -Body (@{ status = "CONFIRMED_VIOLATION"; reason_to_believe_note = "Physical inspection confirmed missing manufacturer address." } | ConvertTo-Json) -ContentType "application/json"
```

The 422 cites Section 15(4), Legal Metrology Act 2009 -- enforced twice
(the sqlite `CHECK` constraint and the API), not just a UI validation.

## Beat 6 -- Signed evidence and the certifiable report

```powershell
curl -Method POST "http://localhost:8000/api/v1/cases/$($case.case_id)/report" -Headers @{ Authorization = "Bearer $env:LMD_INSPECTOR_API_TOKEN"; "X-Inspector-Id" = "demo-inspector" }
curl "http://localhost:8000/api/v1/cases/$($case.case_id)/report" -OutFile report.pdf
```

Open `report.pdf`. Section "Known Limitations of This Analysis" is generated
from the same sentinel files as `/api/v1/limitations` -- the report discloses
its own gaps rather than a judge having to find them.

```powershell
curl http://localhost:8000/api/v1/limitations
```

## What this build does not claim

See `LEGAL_DISCLAIMERS.md` in full. In one line: this is an advisory
pre-screening signal, not a legal adjudication, not a weighment device, not
proof of court-admissibility, and not connected to eMaap or any live
registry.
