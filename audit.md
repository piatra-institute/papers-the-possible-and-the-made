# Audit

## 2026-10-10 — First locally completed edition

Scope: develop the seed into a methodological paper and a bounded recording
experiment. Research, provenance, CSL references, manuscript, code, locked
dependencies, results, figures and version-bound reviews are included.

The user chose the accessible Sue-ware archive after the Dryad route was
unavailable. Downloaded 917 pinned records with blob checksums; raw data and
seed chats remain ignored. The study reports observation sensitivity, not
cultural difference or manufacturing feasibility. Independent pair resampling
and unwhitened PCA were added after the first run and are disclosed as diagnostics.
All original treatments and prior execution receipts remain available.

Verification performed:

- `simulation/.venv/bin/python -B -m unittest discover -s simulation -p 'test_*.py' -v`, from the paper root: 8/8 pass.
- Full recorded `measurement` run, with declared data inputs and results, split and figure artifacts: PASS. See `simulation/README.md` for the exact command and `verification/measurement.json` for hashes/runtime.
- Fresh execution in an isolated temporary copy: `cmp` confirms byte-identical results.json and splits.json in the same environment. The final main run differs from that copy only in a clarified stdout message about distinct arrays, not independent archaeological objects.
- `python3 tooling/papers.py refs the-possible-and-the-made`: all 5 cited IDs resolve; inspected support is separately recorded.
- `python3 tooling/papers.py claims the-possible-and-the-made`: 51 bound entries and required execution PASS.
- `python3 tooling/papers.py voice the-possible-and-the-made` and `lint`: advisory checks complete; 5 contrast/negation candidates and the sentence-rhythm warning reviewed in context.
- `python3 2026/10/the-possible-and-the-made/build.py`: PASS, 11 pages. Initial math delimiters were corrected to Pandoc syntax. Final log has no warning/missing-character matches.
- `pdftoppm -r 115 -png .../paper/PAPER.pdf .../paper/.render/page`: every page viewed. Final rerun changed PDF metadata but none of the rendered page pixels.
- `python3 tooling/papers.py check the-possible-and-the-made --stage local --json`: PASS. Exact report in `verification/local-check.json`.

Shared tooling: `PYTHONPATH=tooling python3 -B -m unittest discover -s tooling/tests -v`
passes all 43 tests. Scaffold guidance, genre-neutral templates and pipeline
documentation now distinguish local completion from separately authorized
publication. Existing unrelated tooling README edits were left untouched.
Scoped changed-file whitespace checks pass. The full tooling diff check reports
only the pre-existing Markdown hard-break whitespace in README.md:16; it was
not changed. A credential-pattern scan of the deliverable files found no matches.

Build logs/manifests, renders, virtual environments, data and chats are ignored.
No commit, push, GitHub repository creation or website update was performed.
This review is local and agent-conducted; it is not external peer review or
validation across archaeological populations.
