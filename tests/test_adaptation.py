"""Rules for adaptation.json, the website-reference-to-prototype handoff.

An artifact may carry several flows, so each derived flow needs its own entry
tying it to the journey and evidence it came from.
"""

import copy
import json
import unittest

from _support import ROOT, adaptation, mentions

FIXTURES = ROOT / "tests" / "fixtures"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class AdaptationRules(unittest.TestCase):
    def setUp(self):
        self.adaptation = load(FIXTURES / "adaptation.json")
        self.reference = load(FIXTURES / "reference.json")
        self.flow = load(FIXTURES / "flow.json")

    def check(self, mutate=None):
        payload = copy.deepcopy(self.adaptation)
        if mutate:
            mutate(payload)
        return adaptation.validate(payload, self.reference, self.flow)

    def entry(self, payload, index=0):
        return payload["adaptations"][index]

    # -- document ------------------------------------------------------- #

    def test_fixture_is_valid(self):
        self.assertEqual(self.check(), [])

    def test_every_derived_flow_declares_its_evidence(self):
        covered = {entry["flowId"] for entry in self.adaptation["adaptations"]}
        declared = {flow["id"] for flow in self.flow["flows"]}
        self.assertEqual(covered, declared)

    def test_hypothesis_is_optional_but_must_match_when_present(self):
        # The fixture deliberately carries one entry with a hypothesis and one without.
        shapes = ["hypothesis" in entry for entry in self.adaptation["adaptations"]]
        self.assertIn(True, shapes)
        self.assertIn(False, shapes)
        found = self.check(lambda d: self.entry(d).update(hypothesis="Something else entirely."))
        self.assertTrue(mentions(found, "hypothesis does not match"))

    def test_retired_shapes_are_rejected_with_guidance(self):
        for version in (1, 2):
            with self.subTest(version=version):
                found = self.check(lambda d: d.update(version=version))
                self.assertTrue(mentions(found, "retired shape", "adaptations"))

    def test_adaptations_array_is_required(self):
        self.assertTrue(mentions(self.check(lambda d: d.update(adaptations=[])), "one entry per derived flow"))

    def test_reference_id_must_match(self):
        found = self.check(lambda d: d["reference"].update(id="some-other-site"))
        self.assertTrue(mentions(found, "reference.id does not match"))

    def test_two_entries_may_not_claim_the_same_flow(self):
        def mutate(payload):
            payload["adaptations"].append(copy.deepcopy(self.entry(payload)))

        self.assertTrue(mentions(self.check(mutate), "Two adaptations claim the same flow"))

    # -- entries -------------------------------------------------------- #

    def test_flow_id_must_name_a_declared_flow(self):
        found = self.check(lambda d: self.entry(d).update(flowId="not-a-flow"))
        self.assertTrue(mentions(found, "declares no flow with that id"))

    def test_task_must_match_the_flow(self):
        found = self.check(lambda d: self.entry(d).update(task="Do something else."))
        self.assertTrue(mentions(found, "task does not match"))

    def test_mode_is_constrained(self):
        self.assertTrue(mentions(self.check(lambda d: self.entry(d).update(mode="pixel-clone")),
                                 "wireframe or visual-reference"))
        self.assertEqual(self.check(lambda d: self.entry(d).update(mode="visual-reference")), [])

    def test_preserve_and_abstract_are_required(self):
        for field in ("preserve", "abstract"):
            with self.subTest(field=field):
                found = self.check(lambda d, f=field: self.entry(d).update({f: []}))
                self.assertTrue(mentions(found, f".{field} needs"))

    def test_cloning_claims_are_rejected(self):
        for claim in ("A pixel-perfect recreation.", "This is a 1:1 copy.", "An exact clone of the site."):
            with self.subTest(claim=claim):
                found = self.check(lambda d, c=claim: self.entry(d).update(claims=[c]))
                self.assertTrue(mentions(found, "unsupported cloning or fidelity claim"))

    def test_journey_must_exist_in_the_reference(self):
        found = self.check(lambda d: self.entry(d).update(journeyId="journey-imaginary"))
        self.assertTrue(mentions(found, "not in reference.json"))

    def test_partial_journey_requires_an_assumption(self):
        reference = copy.deepcopy(self.reference)
        journey_id = self.entry(self.adaptation)["journeyId"]
        for journey in reference["journeys"]:
            if journey["id"] == journey_id:
                journey["status"] = "partial"
        payload = copy.deepcopy(self.adaptation)
        self.entry(payload)["assumptions"] = []
        found = adaptation.validate(payload, reference, self.flow)
        self.assertTrue(mentions(found, "adapts a partial journey and must record an assumption"))

    def test_each_entry_is_checked_independently(self):
        found = self.check(lambda d: self.entry(d, 1).update(flowId="not-a-flow"))
        self.assertTrue(mentions(found, "declares no flow with that id"))


if __name__ == "__main__":
    unittest.main()
