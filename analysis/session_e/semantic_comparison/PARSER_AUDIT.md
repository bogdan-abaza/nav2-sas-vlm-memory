# Deployed-parser compatibility audit

**Results:** `results/parser_audit/` (`PARSER_AUDIT_SUMMARY.json`, `parser_audit_S.csv`, `parser_audit_H.csv`). **Status:** a separately identified check that does not replace the primary results. It was written and tested before the comparison results were inspected.

## Question
The comparison applies one typed response contract in all arms: the target must be a JSON integer, not a boolean, and a missing or non-integer target is a model/parser failure. The deployed navigator parses responses with its own function, which returns the JSON `node_id` value without a type check. The audit asks whether, for every recorded VLM response, the deployed parsing and decision branch would have produced the same outcome class as the comparison's contract.

## Method
All 552 saved API envelopes (300 standardized, 252 historical) were re-parsed offline. The deployed semantics were followed:
- content, or the model's thinking field when content is empty;
- `<think>` blocks and code fences removed;
- direct JSON parsing, then the first `{…}` block;
- no type check;
- the negation guard;
- graph membership and action validation.

Each resulting decision was scored with the same reference as the primary analysis. No model was called.

## Result
0/300 standardized and 0/252 historical observations changed outcome class. The deployed parser returned an integer identifier in 510 cases, including explicit −1 clarifications. It returned a parsing failure in the same 42 cases as the comparison's contract. No boolean or other non-integer identifier occurred in these data.

This establishes compatibility on the observed responses. It does not establish that the two parsers are identical, or that they agree on unobserved response types. The deployed parser's acceptance of a boolean `true` as node 1 is documented in `analysis/session_e/guard_branch/`.

## Availability
The audit script reproduces lines of the protected navigator's parsing code, so it is not published. Its SHA-256 is `765d758222b7bd55386f0e108041444a7caca666379a9bed640cb710a9c4037b`, and it is available to the editor and reviewers in confidence through the journal. The published per-observation tables can be checked against the published raw envelopes in `runs/*/run_primary/records.jsonl`.
