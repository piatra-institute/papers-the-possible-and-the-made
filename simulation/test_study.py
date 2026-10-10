import unittest
import numpy as np
from study import ambiguity, compare, descriptor, object_group, perturb, split_groups


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.x = np.random.default_rng(4).normal(size=(1024, 3))

    def test_zero_treatment_is_identity(self):
        np.testing.assert_array_equal(self.x, perturb(self.x, "uniform", 0, 0, 2))

    def test_mask_size_and_reproducibility(self):
        for mode in ("uniform", "clip"):
            a = perturb(self.x, mode, .75, 0, 2)
            self.assertEqual(len(a), 256)
            np.testing.assert_array_equal(a, perturb(self.x, mode, .75, 0, 2))

    def test_scale_and_translation(self):
        a = descriptor(self.x, 7, "observed")
        np.testing.assert_allclose(a, descriptor(self.x*3+9, 7, "observed"), atol=1e-12)
        np.testing.assert_allclose(descriptor(self.x*3, 7), 3*descriptor(self.x, 7), atol=1e-12)

    def test_oracle_is_explicit_and_differs_after_clipping(self):
        clipped = perturb(self.x, "clip", .75, 0, 4)
        self.assertFalse(np.allclose(descriptor(clipped, 7, "observed"),
                                     descriptor(clipped, 7, "oracle", self.x)))

    def test_group_isolation(self):
        ids = np.array([f"B/B_{i}.txt" for i in range(30)] + ["DC/DC_4.txt"])
        labels = np.array(["B"]*30+["DC"])
        split = split_groups(ids, labels, 17)
        sets = [{object_group(i) for i in ids[m]} for m in split.values()]
        self.assertFalse(sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])

    def test_identical_maps(self):
        x = self.x[:30]
        r, overlap = compare(x, x, np.array(["B"]*15+["P"]*15))
        self.assertEqual(r["overlap"], 1)
        self.assertAlmostEqual(r["distance_rank"], 1)
        self.assertAlmostEqual(r["dispersion_relative_change"], 0)

    def test_inverse_nonuniqueness(self):
        _, _, _, result = ambiguity()
        self.assertEqual(result["observed_max_difference"], 0)
        self.assertGreater(result["relative_volume_difference"], .1)

    def test_invalid_treatment_rejected(self):
        with self.assertRaises(ValueError):
            perturb(self.x, "clip", 1, 0, 2)


if __name__ == "__main__":
    unittest.main()
