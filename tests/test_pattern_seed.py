import json
import unittest

from super_stonks.seed.patterns import FAILURES, build, trace_rows


class PatternSeedTests(unittest.TestCase):
    def test_volume_and_reproducibility(self):
        scenarios = build()
        self.assertEqual(len(scenarios), 5000)
        self.assertEqual(sum(s["is_failure"] for s in scenarios), 4000)
        self.assertEqual(scenarios, build())
        for bucket in FAILURES:
            self.assertEqual(sum(s["bucket"] == bucket for s in scenarios), 500)
        self.assertNotEqual(scenarios, build(seed=1))

    def test_trace_contract_and_retry_ids(self):
        for index, scenario in enumerate(build(2, 4)):
            rows = trace_rows(scenario, "test-run", index, 1000)
            self.assertEqual(rows, trace_rows(scenario, "test-run", index, 1000))
            by_id = {row["span_id"]: row for row in rows}
            self.assertEqual(len(by_id), len(rows))
            root = rows[0]
            self.assertEqual(root["span_attributes"]["name"], "stonks-sessions")
            self.assertEqual(root["span_parents"], [])
            turns = [r for r in rows if r["span_attributes"]["name"].startswith("turn_")]
            self.assertEqual(len(turns), len(scenario["turns"]))
            for row in rows:
                self.assertEqual(row["root_span_id"], root["span_id"])
                self.assertTrue(row["metadata"]["synthetic"])
                self.assertEqual(row["metadata"]["timing_source"], "simulated")
                self.assertLess(row["metrics"]["start"], row["metrics"]["end"])
                for parent_id in row["span_parents"]:
                    parent = by_id[parent_id]
                    self.assertLessEqual(parent["metrics"]["start"], row["metrics"]["start"])
                    self.assertGreaterEqual(parent["metrics"]["end"], row["metrics"]["end"])
            for turn in turns:
                children = [r for r in rows if r["span_parents"] == [turn["span_id"]]]
                self.assertIsInstance(turn["input"], str)
                self.assertIsInstance(turn["output"], str)
                self.assertTrue(any(c["span_attributes"]["type"] == "llm" for c in children))
                calls = [c for c in children if c["span_attributes"]["type"] == "tool"]
                self.assertEqual([c["span_attributes"]["name"] for c in calls], turn["metadata"]["tool_names"])
            json.dumps(rows)  # upload must be serializable without SDK-specific objects

    def test_behavior_evidence_is_in_inputs_and_outputs(self):
        for scenario in build(10, 20):
            bucket, turns = scenario["bucket"], scenario["turns"]
            last = turns[-1]
            if bucket == "wrong_ticker_followup":
                first_ticker = turns[0]["ticker"]
                self.assertEqual(last["ticker"], first_ticker)
                self.assertNotIn(first_ticker, last["input"])
                self.assertIn(first_ticker, last["output"])
            elif bucket == "contradicted_tool_verdict":
                self.assertEqual(last["tool_output"]["verdict"], "SELL")
                self.assertIn("BUY", last["output"])
            elif bucket == "ignored_tool_error":
                self.assertIn("error", last["tool_output"])
                self.assertIn("BUY", last["output"])
            elif bucket == "fabricated_live_price":
                self.assertIsNone(last["tool_output"])
                self.assertIn("$", last["output"])
            elif bucket == "grounded_research":
                result = last["tool_output"]
                self.assertIn(result["verdict"], last["output"])
                self.assertIn(str(result["signals"]["rsi_14"]), last["output"])

    def test_invalid_volume(self):
        for count, controls in [(0, 1), (-1, 0), (1, -1)]:
            with self.assertRaises(ValueError):
                build(count, controls)


if __name__ == "__main__":
    unittest.main()
