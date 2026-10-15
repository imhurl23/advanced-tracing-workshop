from collections import Counter
import unittest

from super_stonks.seed.recurring import FAMILIES, build


class RecurringSeedTests(unittest.TestCase):
    def test_balanced_volume_and_selected_families(self):
        scenarios = build(1200, seed=42)
        self.assertEqual(Counter(s["scenario_family"] for s in scenarios),
                         {family: 400 for family in FAMILIES})
        selected = build(101, families=FAMILIES[:2])
        counts = Counter(s["scenario_family"] for s in selected)
        self.assertEqual(set(counts), set(FAMILIES[:2]))
        self.assertEqual(sorted(counts.values()), [50, 51])

    def test_only_user_inputs_are_generated(self):
        scenarios = build(1200, seed=42)
        self.assertEqual(scenarios, build(1200, seed=42))
        self.assertNotEqual(scenarios, build(1200, seed=43))
        for scenario in scenarios:
            self.assertNotIn("output", scenario)
            self.assertTrue(all(isinstance(turn, str) and turn for turn in scenario["turns"]))
        self.assertTrue(any(len(s["turns"]) == 2 for s in scenarios))
        for family in FAMILIES:
            self.assertEqual({s["variant"] for s in scenarios if s["scenario_family"] == family}, set(range(6)))

    def test_invalid_selection(self):
        for count, families in [(0, FAMILIES), (1, ()), (1, ("unknown",))]:
            with self.assertRaises(ValueError):
                build(count, families=families)


if __name__ == "__main__":
    unittest.main()
