---
name: iron-bottom-sound-rules
description: Retrieve, verify, structure, implement, and explain Iron Bottom Sound IV rules from this project's Chinese rulebook, player tables, scenario book, ship records, maps, and counters. Use for rule questions, scenario legality, engine adjudication, data transcription, tutorials, and AI explanations; do not use for Harpoon or unrelated naval games.
---

# Iron Bottom Sound IV rule verification

Treat `resources/originals/manifest.json` as the source inventory. The mandatory rules set is the Chinese rulebook, player-aid tables, scenario book, ship-record manual, ship list, movement/attack sheet, maps, counters, and ship-class strips.

## Authority

Apply this precedence and record every discrepancy:

1. Scenario-specific rule.
2. Ship record or player-aid table.
3. General rulebook.

Never borrow a Harpoon rule. Historical plausibility is not authority for this game.

## Required workflow

- Before answering or changing adjudication logic, run `python skills/iron-bottom-sound-rules/scripts/query_rules.py "<concept or table>"`.
- Open the returned original PDF page or image. OCR is retrieval evidence only; visually verify every table cell, firing arc, counter value, map anchor, modifier, priority and rounding rule.
- Assign or reuse a stable `IBS-R-*`, `IBS-T-*`, `IBS-S-*`, or `IBS-U-*` identifier.
- Keep rule data outside UI, API, storage and LLM code.
- A rule is complete only when its source, structured data, engine call site, event trace and boundary tests all exist.
- If a required fact is unresolved, block automatic adjudication and add it to `docs/rules/open_questions.md`.
- Use [references/audit.md](references/audit.md) when assessing coverage or changing engine behavior.
- Use [references/corpus.md](references/corpus.md) when rebuilding or diagnosing retrieval data.

## Retrieval

```powershell
python skills/iron-bottom-sound-rules/scripts/build_rule_corpus.py
python skills/iron-bottom-sound-rules/scripts/query_rules.py "炮击命中表 射程修正"
python skills/iron-bottom-sound-rules/scripts/query_rules.py "想定3 通道行动"
```
