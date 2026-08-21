"""Rules for reference.json, the website research artifact."""

import copy
import json
import unittest

from _support import ROOT, mentions, reference

REFERENCE_DIR = ROOT / "tests" / "fixtures"


class ReferenceRules(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((REFERENCE_DIR / "reference.json").read_text(encoding="utf-8"))

    def check(self, mutate=None, base_dir=REFERENCE_DIR):
        payload = copy.deepcopy(self.data)
        if mutate:
            mutate(payload)
        return reference.validate(payload, base_dir)

    def test_fixture_is_valid(self):
        self.assertEqual(self.check(), [])

    def test_evidence_is_required(self):
        self.assertTrue(mentions(self.check(lambda d: d.update(evidence=[])), "At least one evidence record"))

    def test_observation_must_cite_known_evidence(self):
        def mutate(data):
            data["observations"][0]["evidence"] = ["ev-does-not-exist"]

        self.assertTrue(mentions(self.check(mutate), "cites unknown evidence"))

    def test_observation_kind_is_constrained(self):
        def mutate(data):
            data["observations"][0]["kind"] = "assumed"

        self.assertTrue(mentions(self.check(mutate), "must be observed or inferred"))

    def test_journey_status_is_constrained(self):
        def mutate(data):
            data["journeys"][0]["status"] = "probably"

        self.assertTrue(mentions(self.check(mutate), "needs a valid status"))

    def test_journey_needs_at_least_two_steps(self):
        def mutate(data):
            data["journeys"][0]["steps"] = ["Open the page"]

        self.assertTrue(mentions(self.check(mutate), "at least two steps"))

    def test_limitations_must_be_recorded(self):
        self.assertTrue(mentions(self.check(lambda d: d.update(limitations=[])), "limitations must contain"))

    def test_source_url_must_be_http(self):
        def mutate(data):
            data["source"]["url"] = "file:///tmp/page.html"

        self.assertTrue(mentions(self.check(mutate), "must be an http(s) URL"))

    def test_captured_at_must_be_iso_8601(self):
        def mutate(data):
            data["source"]["capturedAt"] = "yesterday afternoon"

        self.assertTrue(mentions(self.check(mutate), "must be ISO 8601"))

    def test_screenshot_evidence_must_point_at_a_real_file(self):
        def mutate(data):
            data["evidence"].append({
                "id": "ev-ghost-shot",
                "kind": "screenshot",
                "method": "browser",
                "path": "screenshots/never-captured.png",
                "url": data["source"]["url"],
                "capturedAt": data["source"]["capturedAt"],
                "viewport": "desktop",
            })

        found = self.check(mutate)
        self.assertTrue(mentions(found, "points at a missing file"))

    def test_screenshot_evidence_needs_a_path(self):
        def mutate(data):
            data["evidence"].append({
                "id": "ev-pathless-shot",
                "kind": "screenshot",
                "method": "browser",
                "url": data["source"]["url"],
                "capturedAt": data["source"]["capturedAt"],
            })

        self.assertTrue(mentions(self.check(mutate), "needs a path"))


if __name__ == "__main__":
    unittest.main()
