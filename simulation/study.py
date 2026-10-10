"""Paired recording-robustness study. No cultural or feasibility classifier."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys
import unittest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy.spatial.distance import pdist, squareform
from scipy.stats import spearmanr
import torch
from torch import nn

HERE = Path(__file__).resolve().parent
SEEDS = (17, 29, 43)
METHODS = ("descriptor", "pca", "pca_unwhitened", "autoencoder")
QUANTILES = np.linspace(.01, .99, 64)
torch.set_num_threads(2)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def object_group(name):
    return Path(name).stem.split("_", 1)[-1].casefold()


def load_data():
    manifest = json.loads((HERE / "data-manifest.json").read_text())
    archive = HERE / "data/clouds.npz"
    if digest(archive) != manifest["archive_sha256"]:
        raise ValueError("Data archive differs from the provenance manifest")
    with np.load(archive, allow_pickle=False) as data:
        xyz, ids, labels = data["xyz"], data["ids"], data["labels"]
    if len(xyz) != manifest["count"] or xyz.shape[1:] != (1024, 3):
        raise ValueError("Unexpected input shape")
    unique, seen, duplicates = [], {}, []
    for i, cloud in enumerate(xyz):
        key = hashlib.sha256(cloud.tobytes()).hexdigest()
        if key in seen:
            if labels[i] != labels[seen[key]]:
                raise ValueError("Exact duplicate with conflicting category")
            duplicates.append(str(ids[i]))
        else:
            seen[key] = i
            unique.append(i)
    return xyz[unique], ids[unique], labels[unique], duplicates


def split_groups(ids, labels, seed):
    rng = np.random.default_rng(seed)
    groups = np.array([object_group(i) for i in ids])
    assignment = {}
    for label in sorted(set(labels)):
        available = sorted(g for g in set(groups[labels == label]) if g not in assignment)
        rng.shuffle(available)
        n = max(1, round(len(available) * .2))
        for i, group in enumerate(available):
            assignment[group] = "test" if i < n else "val" if i < 2*n else "train"
    masks = {part: np.array([assignment[g] == part for g in groups])
             for part in ("train", "val", "test")}
    assert np.all(sum(m.astype(int) for m in masks.values()) == 1)
    return masks


def radius(x):
    return float(np.linalg.norm(x - x.mean(axis=0), axis=1).max())


def descriptor(x, seed, normalization="raw", reference=None):
    scale = 1.0 if normalization == "raw" else radius(x if reference is None else reference)
    if scale <= 0:
        raise ValueError("Degenerate cloud")
    rng = np.random.default_rng(seed)
    pairs = rng.integers(0, len(x), (8192, 2))
    distances = np.linalg.norm(x[pairs[:, 0]] - x[pairs[:, 1]], axis=1) / scale
    return np.quantile(distances, QUANTILES)


def perturb(x, mode, loss, noise, seed):
    if not 0 <= loss < 1 or noise < 0:
        raise ValueError("Invalid perturbation")
    rng = np.random.default_rng(seed)
    count = max(2, int(round(len(x) * (1-loss))))
    if loss == 0:
        keep = np.arange(len(x))
    elif mode == "uniform":
        keep = np.sort(rng.choice(len(x), count, replace=False))
    elif mode == "clip":
        direction = rng.normal(size=3)
        keep = np.sort(np.argsort(x @ direction, kind="stable")[:count])
    else:
        raise ValueError("Unknown mask")
    # Paired noise for a point is the same regardless of which other points survive.
    jitter = np.random.default_rng(seed + 99991).normal(size=x.shape)
    return x[keep] + noise * np.linalg.norm(np.ptp(x, axis=0)) * jitter[keep]


class Representation:
    def __init__(self, x, val, seed):
        self.mean = x.mean(0)
        self.std = np.maximum(x.std(0), 1e-9)
        z = (x - self.mean) / self.std
        self.pcs = np.linalg.svd(z, full_matrices=False)[2][:8].T
        torch.manual_seed(seed)
        self.encoder = nn.Sequential(nn.Linear(64, 32), nn.Tanh(), nn.Linear(32, 8))
        self.decoder = nn.Sequential(nn.Linear(8, 32), nn.Tanh(), nn.Linear(32, 64))
        model = nn.Sequential(self.encoder, self.decoder)
        optimizer = torch.optim.Adam(model.parameters(), lr=.001)
        tx = torch.tensor(z, dtype=torch.float32)
        vx = torch.tensor((val - self.mean) / self.std, dtype=torch.float32)
        best, waiting, best_state = float("inf"), 0, None
        generator = torch.Generator().manual_seed(seed)
        for epoch in range(300):
            model.train()
            for batch in torch.randperm(len(tx), generator=generator).split(128):
                optimizer.zero_grad()
                loss = nn.functional.mse_loss(model(tx[batch]), tx[batch])
                loss.backward()
                optimizer.step()
            model.eval()
            with torch.no_grad():
                validation = float(nn.functional.mse_loss(model(vx), vx))
            if validation < best - 1e-7:
                best, waiting = validation, 0
                best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            else:
                waiting += 1
            if waiting == 30:
                break
        model.load_state_dict(best_state)
        self.training = {"epochs": epoch+1, "validation_mse": best}
        self.latent_stats = {}
        for method in ("pca", "autoencoder"):
            embedding = self.embed(x, method, standardize=False)
            self.latent_stats[method] = (embedding.mean(0), np.maximum(embedding.std(0), 1e-9))

    def embed(self, x, method, standardize=True):
        z = (x-self.mean)/self.std
        if method == "descriptor":
            return z
        if method in ("pca", "pca_unwhitened"):
            z = z @ self.pcs
            if method == "pca_unwhitened":
                return z
        elif method == "autoencoder":
            with torch.no_grad():
                z = self.encoder(torch.tensor(z, dtype=torch.float32)).numpy()
        else:
            raise ValueError(method)
        if standardize:
            mean, std = self.latent_stats[method]
            z = (z-mean)/std
        return z


def compare(reference, changed, labels):
    a, b = pdist(reference), pdist(changed)
    ma, mb = squareform(a), squareform(b)
    np.fill_diagonal(ma, np.inf)
    np.fill_diagonal(mb, np.inf)
    k = min(10, len(labels)-1)
    na, nb = np.argsort(ma, axis=1)[:, :k], np.argsort(mb, axis=1)[:, :k]
    overlap = np.array([len(set(x) & set(y))/k for x, y in zip(na, nb)])
    i, j = np.triu_indices(len(labels), 1)
    same = labels[i] == labels[j]
    ratio_a = float(np.mean(a[same]**2)/np.mean(a[~same]**2))
    ratio_b = float(np.mean(b[same]**2)/np.mean(b[~same]**2))
    return {"overlap": float(overlap.mean()), "distance_rank": float(spearmanr(a, b).statistic),
            "dispersion_reference": ratio_a, "dispersion_changed": ratio_b,
            "dispersion_relative_change": ratio_b/ratio_a-1}, overlap


def ambiguity():
    z = np.linspace(0, 1, 1001)
    a = .5 + .1*z
    b = a + .3*np.maximum(0, 1-z/.6)**2
    visible = z >= .6
    volumes = [float(np.pi*np.trapezoid(r*r, z)) for r in (a, b)]
    return z, a, b, {"observed_max_difference": float(np.max(np.abs(a[visible]-b[visible]))),
                      "reference_volume": volumes[0], "alternative_volume": volumes[1],
                      "relative_volume_difference": volumes[1]/volumes[0]-1}


def main():
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    xyz, ids, labels, duplicates = load_data()
    print(f"Loaded {len(ids)} distinct position arrays after exact duplicate audit", flush=True)
    normalizations = ("raw", "observed", "oracle")
    full = {norm: np.stack([descriptor(x, 10000+i, norm) for i, x in enumerate(xyz)])
            for norm in normalizations}
    conditions = [(mode, loss, noise) for mode in ("uniform", "clip")
                  for loss in (0., .25, .5, .75) for noise in (0., .0025, .01)
                  if not (mode == "clip" and loss == 0)]
    rows, split_records, trainers = [], [], []
    models = {}
    for seed in SEEDS:
        split = split_groups(ids, labels, seed)
        split_records.append({"seed": seed, **{k: ids[v].tolist() for k, v in split.items()}})
        for norm in ("raw", "observed"):
            model = Representation(full[norm][split["train"]], full[norm][split["val"]], seed)
            models[(seed, norm)] = model
            trainers.append({"seed": seed, "normalization": norm, **model.training})
    for mode, loss, noise in conditions:
        disturbed = [perturb(x, mode, loss, noise, 30000+i) for i, x in enumerate(xyz)]
        for norm in normalizations:
            features = np.stack([descriptor(x, 10000+i, norm, xyz[i] if norm == "oracle" else None)
                                 for i, x in enumerate(disturbed)])
            for seed in SEEDS:
                mask = split_groups(ids, labels, seed)["test"]
                model = models[(seed, "observed" if norm == "oracle" else norm)]
                for method in METHODS:
                    stats, per_object = compare(model.embed(full[norm][mask], method),
                                                model.embed(features[mask], method), labels[mask])
                    if seed == SEEDS[0]:
                        rng = np.random.default_rng(920)
                        draws = rng.choice(per_object, (1000, len(per_object)), replace=True).mean(1)
                        stats["overlap_ci95_conditional"] = np.quantile(draws, [.025, .975]).tolist()
                    rows.append({"seed": seed, "normalization": norm, "method": method,
                                 "mask": mode, "loss": loss, "noise": noise, **stats})
        print(f"completed {mode}, loss={loss}, noise={noise}", flush=True)
    sampling_controls, compression_controls = [], []
    for norm in ("raw", "observed"):
        resampled = np.stack([descriptor(x, 710000+i, norm) for i, x in enumerate(xyz)])
        for seed in SEEDS:
            mask = split_groups(ids, labels, seed)["test"]
            model = models[(seed, norm)]
            for method in METHODS:
                stats, _ = compare(model.embed(full[norm][mask], method),
                                   model.embed(resampled[mask], method), labels[mask])
                sampling_controls.append({"seed": seed, "normalization": norm, "method": method, **stats})
                compression, _ = compare(model.embed(full[norm][mask], "descriptor"),
                                         model.embed(full[norm][mask], method), labels[mask])
                compression_controls.append({"seed": seed, "normalization": norm, "method": method, **compression})
    z, a, b, inverse = ambiguity()
    output = HERE / "output"
    output.mkdir(exist_ok=True)
    figures = HERE.parent / "paper/figures"
    figures.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.dpi": 150})
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.plot(a, z, label="Profile A", color="#1c5268")
    ax.plot(b, z, label="Profile B", color="#b56638", linestyle="--")
    ax.axhspan(.6, 1, color="#d5ded6", alpha=.6, label="Observed interval")
    ax.set(xlabel="Radius (arbitrary units)", ylabel="Height", xlim=(0, .9))
    ax.legend(loc="lower left", frameon=False)
    fig.tight_layout()
    fig.savefig(figures / "ambiguity.pdf")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.1), sharey=True)
    for ax, mode in zip(axes, ("uniform", "clip")):
        for method, color in zip(("descriptor", "pca_unwhitened", "autoencoder"), ("#1c5268", "#b56638", "#687942")):
            losses = (0., .25, .5, .75)
            means, lo, hi = [], [], []
            for loss in losses:
                values = [r["overlap"] for r in rows if r["normalization"] == "observed"
                          and r["method"] == method and r["loss"] == loss and r["noise"] == 0
                          and r["mask"] == ("uniform" if loss == 0 else mode)]
                means.append(np.mean(values)); lo.append(min(values)); hi.append(max(values))
            ax.plot(np.array(losses)*100, means, "o-", label=method.replace("pca_unwhitened", "PCA (unwhitened)"), color=color)
            ax.fill_between(np.array(losses)*100, lo, hi, alpha=.12, color=color)
        ax.set(title="Uniform point loss" if mode == "uniform" else "Contiguous clipping",
               xlabel="Points removed (%)", ylim=(0, 1.04), xticks=[0,25,50,75])
    axes[0].set_ylabel("Ten-neighbour overlap")
    axes[1].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(figures / "recording.pdf")
    plt.close(fig)
    selected = {}
    for key, criteria in {
        "uniform_half_descriptor": ("uniform", .5, "descriptor"),
        "clip_half_descriptor": ("clip", .5, "descriptor"),
        "clip_half_pca": ("clip", .5, "pca"),
        "clip_half_pca_unwhitened": ("clip", .5, "pca_unwhitened"),
        "clip_half_autoencoder": ("clip", .5, "autoencoder"),
    }.items():
        selected[key] = next(r for r in rows if r["seed"] == 17 and r["normalization"] == "observed"
                             and r["noise"] == 0 and (r["mask"], r["loss"], r["method"]) == criteria)
    results = {"design": "conditional recording sensitivity, not cultural inference",
               "dataset": {"records": len(ids), "points": 1024, "duplicates_excluded": duplicates,
                           "groups": len(set(object_group(i) for i in ids)),
                           "categories": {str(c): int(sum(labels == c)) for c in sorted(set(labels))}},
               "synthetic": inverse, "headline": selected, "rows": rows, "training": trainers,
               "sampling_controls": sampling_controls, "compression_controls": compression_controls}
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    (output / "splits.json").write_text(json.dumps(split_records, indent=2) + "\n")
    execution = {"execution": {"status": "PASS", "exit_code": 0},
                 "runtime": {"python": sys.version, "platform": platform.platform(),
                             "numpy": np.__version__, "scipy": scipy.__version__, "torch": torch.__version__},
                 "experiments": [{"name": name, "required": True, "execution": {"status": "PASS", "exit_code": 0}}
                                 for name in ("unit-tests", "data-audit", "split-audit", "all-recording-conditions", "sampling-control", "compression-control", "synthetic-inverse-example")],
                 "unit_tests": result.testsRun, "condition_method_split_rows": len(rows)}
    (output / "execution.json").write_text(json.dumps(execution, indent=2) + "\n")
    print(json.dumps(results["headline"], indent=2))


if __name__ == "__main__":
    main()
