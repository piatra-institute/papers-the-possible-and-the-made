# Recording sensitivity study

The input is the CC BY 4.0 CeramicNet supplement by Wataru Tatsuda, Ryo Hori,
Kimiyasu Morikawa and Hayata Inoue, associated with DOI 10.1016/j.jas.2026.106472:
https://github.com/dv-wataru-tatsuda/ceramicnet-supplement

Pinned revision: 15c4cd4b8211afcb556deed8774ed226638494f7.
The raw archive stays out of Git. data-manifest.json records every selected
upstream blob and SHA-256; the analysis verifies the assembled archive hash.
No upstream executable code is run. Download needs public network access.

## Reproduce

From this directory, with Python 3.12 and uv:

```sh
uv sync --frozen
uv run --frozen python fetch_data.py
MPLCONFIGDIR=.cache/matplotlib uv run --frozen python study.py
```

Eight unit tests run before the analysis. Tests alone:

```sh
uv run --frozen python -m unittest discover -v
```

protocol.md specifies the original comparisons and records the two diagnostic
extensions after the first run. output/results.json contains every treatment,
including ordinary and whitened PCA, raw/observed/oracle normalization,
sampling and compression controls. output/splits.json contains exact record
allocations. Counts and figures are generated, not transcribed inputs.

The reported run used the lock-created .venv/bin/python directly; an intervening
uv invocation failed because the sandbox denied access to the default uv cache.
Its failed receipt is retained. The successful final receipt identifies the
actual interpreter and libraries. A command failure is not a negative finding.

## Workspace evidence record

Run from the collection root after retrieving the data:

```sh
MPLCONFIGDIR=.cache/matplotlib python3 tooling/papers.py run the-possible-and-the-made --id measurement --cwd simulation --input simulation/data/clouds.npz --input simulation/data-manifest.json --artifact simulation/output/results.json --artifact simulation/output/splits.json --artifact paper/figures/ambiguity.pdf --artifact paper/figures/recording.pdf --execution-result simulation/output/execution.json -- .venv/bin/python study.py
```

Re-running regenerates figures and changes their PDF timestamps; rebuild the
manuscript afterwards. Numerical repeatability is checked separately from binary
PDF identity. The figures show mean/range across fixed splits; bootstrap intervals
are conditional on a fixed reference gallery and do not describe cultural populations.
