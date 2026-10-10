"""Fetch only the pinned, CC-BY-4.0 CeramicNet observations; verify Git blobs.

No source-repository code is executed. Network access is needed only here.
The analysis subsequently verifies the resulting NPZ against data-manifest.json.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.request

import numpy as np

REVISION = "15c4cd4b8211afcb556deed8774ed226638494f7"
REPO = "dv-wataru-tatsuda/ceramicnet-supplement"
HERE = Path(__file__).resolve().parent
CLASSES = {"B", "DB", "DBR", "DC", "P"}


def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                return response.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def git_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def main():
    data_dir = HERE / "data"
    data_dir.mkdir(exist_ok=True)
    tree = json.loads(get(f"https://api.github.com/repos/{REPO}/git/trees/{REVISION}?recursive=1"))
    if tree.get("truncated"):
        raise RuntimeError("Incomplete Git tree")
    entries = sorted(
        (e for e in tree["tree"] if e["type"] == "blob"
         and len(e["path"].split("/")) == 3
         and e["path"].split("/")[0] == "ceramicnet_data"
         and e["path"].split("/")[1] in CLASSES
         and e["path"].endswith(".txt")), key=lambda e: e["path"])

    def fetch(entry):
        path = data_dir / entry["path"]
        if path.exists() and git_sha(path.read_bytes()) == entry["sha"]:
            raw = path.read_bytes()
        else:
            raw = get(f"https://raw.githubusercontent.com/{REPO}/{REVISION}/{entry['path']}")
            if git_sha(raw) != entry["sha"]:
                raise ValueError(f"Git checksum mismatch: {entry['path']}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        array = np.loadtxt(io.BytesIO(raw), dtype=np.float64)
        if array.shape != (1024, 6) or not np.isfinite(array).all():
            raise ValueError(f"Unexpected point cloud: {entry['path']}, {array.shape}")
        return array[:, :3], {
            "path": entry["path"], "git_blob": entry["sha"],
            "sha256": hashlib.sha256(raw).hexdigest(),
            "xyz_sha256": hashlib.sha256(array[:, :3].tobytes()).hexdigest(),
        }

    observations, records = [], []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, (xyz, record) in enumerate(pool.map(fetch, entries), 1):
            observations.append(xyz)
            records.append(record)
            if i % 100 == 0:
                print(f"verified {i}/{len(entries)} clouds", flush=True)
    for name in ("README.md", "LICENSE", "CITATION.cff"):
        (data_dir / name).write_bytes(get(f"https://raw.githubusercontent.com/{REPO}/{REVISION}/{name}"))
    archive = data_dir / "clouds.npz"
    np.savez_compressed(
        archive, xyz=np.stack(observations),
        ids=np.array([r["path"] for r in records]),
        labels=np.array([r["path"].split("/")[1] for r in records]))
    manifest = {
        "repository": f"https://github.com/{REPO}", "revision": REVISION,
        "license": "CC-BY-4.0", "doi": "10.1016/j.jas.2026.106472",
        "units": "archive coordinate units; physical calibration not established",
        "excluded": ["other_data/DCFLIP (derived upside-down copies)", "normals"],
        "count": len(records), "points_per_cloud": 1024,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": records,
    }
    (HERE / "data-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"saved {len(records)} verified clouds", flush=True)


if __name__ == "__main__":
    main()
