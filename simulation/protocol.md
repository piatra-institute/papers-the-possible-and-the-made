# Measurement protocol

Frozen before comparison results, 2026-10-10. Changes must be recorded below.

## Question and reference

How much do recording loss and representation compression change a map of the
supplied Sue-ware observations? Complete input clouds are the reference, not
physical ground truth. Use XYZ only; ignore normals and category labels during
representation fitting. Archive coordinate units have not been physically
calibrated. Preserve their relative scale in one condition; normalize by the
observed cloud's maximum centred radius in the other.

## Representation and split

Use 64 quantiles (0.01 through 0.99) of the sampled pairwise point-distance
distribution (D2); 8192 pairs, reproducibly seeded per observation. This
rotation-invariant descriptor deliberately loses spatial arrangement.
Compare the descriptor itself with 8-dimensional PCA and a compact
64-32-8-32-64 tanh autoencoder fitted to standardized complete training
descriptors. Use Adam, learning rate 0.001, at most 300 epochs, patience 30,
batch size 128, validation loss only. All metrics use 64-dimensional descriptor
space or standardized latent coordinates fitted on training data as applicable.

Use seeds 17, 29 and 43; per seed hold out 20% of source-object groups for test
and 20% for validation, stratified by supplied category where possible.
Collapse exact duplicate XYZ clouds. Group case-insensitive source identifiers
across category prefixes and repeated records before splitting. Do not claim a
site, workshop or potter holdout when these cannot be established from metadata.
No derived perturbation crosses its source-object split.

## Interventions and metrics

Remove 0%, 25%, 50% and 75% of points by uniform subsampling or a contiguous
half-space cut in a reproducibly sampled direction. Add independent Gaussian
noise at 0%, 0.25% or 1% of the reference bounding-box diagonal. The reference
diagonal sets the experimental noise treatment, not a model input. Use the
same observations and perturbations for every representation and normalization.
Run full-cloud normalization only as a labelled oracle diagnostic.

For each fixed test gallery compare complete versus perturbed maps:
mean overlap of the ten nearest neighbours; Spearman correlation of pairwise
distances; and mean within-category squared distance divided by mean
between-category squared distance. Report proportional change in this last
ratio. Category is a morphological archive label, not a social group.
Give 95% percentile intervals from object-row bootstrap of neighbourhood
overlap (1000 resamples) for the first split, and ranges across the three
predefined splits. These intervals are conditional on the fixed reference
gallery; they are not cultural-population confidence intervals.

## Analytical demonstration

Construct two rotational radius profiles identical on an observed top interval
but different below it. Calculate their volume difference and show both profiles.
This proves a particular inverse problem non-unique, not a claim about the
manufacturability of either generated form.

## Recorded amendment after the first complete run

2026-10-10: Uniform thinning changed neighbourhoods substantially. Add an
independent pair-sampling control on unchanged complete point clouds, using
the same fitted representations and splits but descriptor seeds 710000+i.
This separates finite descriptor sampling from missing geometry. Keep every
original condition and report this control regardless of its outcome. The
initial execution receipt is retained; no parameter or headline condition was
selected to improve the comparative ranking.

The control showed substantial instability in the whitened PCA map. Add ordinary
unwhitened PCA with the identical fitted components, keeping the original
whitened PCA results. Also compare each complete-data embedding with the complete
descriptor map. These controls distinguish low-variance amplification by
whitening from dimensionality reduction itself. Treat them as diagnostic
extensions, not preregistered confirmations. Do not generalize the poor whitening
result to PCA or geometric analysis as a whole.

## Success and failure

Successful execution means all tests and declared conditions ran. Stability,
poor autoencoder performance and reversals of method ranking are valid findings.
Do not infer functional equivalence, a manufacturing frontier, global intrinsic
dimension, cultural causes or authentic missing geometry from these metrics.
