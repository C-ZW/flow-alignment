"""Rules for adaptation.json, the website-reference-to-prototype handoff.

An artifact may carry several flows, so each derived flow needs its own entry
tying it to the journey and evidence it came from.
"""

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

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

    def test_boolean_is_not_version_one(self):
        self.assertTrue(mentions(
            self.check(lambda payload: payload.update({"version": True})),
            "version must equal 1",
        ))

    def test_id_must_match_the_prototype_directory_when_supplied(self):
        found = adaptation.validate(
            copy.deepcopy(self.adaptation),
            self.reference,
            self.flow,
            artifact_dir_name="different-folder",
        )
        self.assertTrue(mentions(found, "must match its prototype directory", "different-folder"))

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

    def test_invalid_version_is_rejected(self):
        found = self.check(lambda d: d.update(version=99))
        self.assertTrue(mentions(found, "adaptation.version must equal 1"))

    def test_adaptations_array_is_required(self):
        self.assertTrue(mentions(self.check(lambda d: d.update(adaptations=[])), "one entry per derived flow"))

    def test_reference_id_must_match(self):
        found = self.check(lambda d: d["reference"].update(id="some-other-site"))
        self.assertTrue(mentions(found, "reference.id does not match"))

    def test_reference_path_must_exist(self):
        found = self.check(lambda d: d["reference"].update(path="tests/fixtures/missing-reference.json"))
        self.assertTrue(mentions(found, "does not point to an existing reference JSON"))

    def test_reference_path_must_stay_repository_relative(self):
        for path in ("../reference.json", "..\\reference.json", "C:\\reference.json"):
            with self.subTest(path=path):
                found = self.check(lambda d, selected=path: d["reference"].update(path=selected))
                self.assertTrue(mentions(found, "repository-relative", "parent traversal"))

    def test_reference_path_must_resolve_to_the_supplied_reference_id(self):
        found = self.check(
            lambda d: d["reference"].update(
                path="references/behind-your-day/reference.json"
            )
        )
        self.assertTrue(mentions(found, "different reference JSON"))

    def test_reference_path_and_supplied_file_contents_must_match(self):
        supplied_path = FIXTURES / "reference.json"
        payload = copy.deepcopy(self.adaptation)
        self.assertEqual(
            adaptation.validate(
                payload,
                self.reference,
                self.flow,
                reference_path=supplied_path,
                base_dir=ROOT,
            ),
            [],
        )
        supplied = copy.deepcopy(self.reference)
        supplied["id"] = "different-site"
        found = adaptation.validate(
            payload,
            supplied,
            self.flow,
            reference_path=supplied_path,
            base_dir=ROOT,
        )
        self.assertTrue(mentions(found, "does not match the reference JSON supplied"))

    def test_reference_path_must_not_escape_base_directory_through_a_symlink(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks are unavailable on this platform")
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary) / "repo"
            outside = Path(temporary) / "outside-reference.json"
            base.mkdir()
            (base / "references").mkdir()
            outside.write_text(json.dumps(self.reference), encoding="utf-8")
            link = base / "references" / "reference.json"
            try:
                link.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")

            payload = copy.deepcopy(self.adaptation)
            payload["reference"]["path"] = "references/reference.json"
            found = adaptation.validate(
                payload,
                self.reference,
                self.flow,
                reference_path=link,
                base_dir=base,
            )
            self.assertTrue(mentions(found, "resolve inside the repository/base directory", "symlink"))

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
        found = self.check(lambda d: self.entry(d).update(mode="visual-reference"))
        self.assertTrue(mentions(found, "visualReference is required", "generic layout"))

    def test_visual_reference_requires_a_screenshot_backed_layout_map(self):
        payload = copy.deepcopy(self.adaptation)
        reference = copy.deepcopy(self.reference)
        reference["evidence"].append({
            "id": "ev-shot",
            "kind": "screenshot",
            "method": "browser",
            "path": "screenshots/pricing.png",
            "url": "https://example.com/pricing",
            "capturedAt": "2026-08-21T10:00:00+08:00",
            "viewport": "desktop",
        })
        self.entry(payload).update({
            "mode": "visual-reference",
            "visualReference": {
                "evidence": ["ev-shot"],
                "shell": ["Horizontal marketing navigation"],
                "hierarchy": ["Hero followed by plan comparison"],
                "density": ["Two plan cards in one desktop row"],
            },
        })
        self.assertEqual(adaptation.validate(payload, reference, self.flow), [])

    def test_visual_reference_rejects_non_screenshot_evidence(self):
        def mutate(payload):
            self.entry(payload).update({
                "mode": "visual-reference",
                "visualReference": {
                    "evidence": ["ev-page"],
                    "shell": ["Horizontal marketing navigation"],
                    "hierarchy": ["Hero followed by plan comparison"],
                    "density": ["Two plan cards in one desktop row"],
                },
            })

        found = self.check(mutate)
        self.assertTrue(mentions(found, "ev-page", "not a screenshot"))

    def test_visual_reference_requires_each_structural_dimension(self):
        for field in ("shell", "hierarchy", "density"):
            with self.subTest(field=field):
                def mutate(payload, missing=field):
                    self.entry(payload).update({
                        "mode": "visual-reference",
                        "visualReference": {
                            "evidence": ["ev-page"],
                            "shell": ["Horizontal navigation"],
                            "hierarchy": ["Hero then cards"],
                            "density": ["Two cards per row"],
                        },
                    })
                    self.entry(payload)["visualReference"][missing] = []

                found = self.check(mutate)
                self.assertTrue(mentions(found, f"visualReference.{field}", "layout decision"))

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

    def test_malformed_member_shapes_return_validation_errors(self):
        for mutate, fragment in (
            (lambda d: self.entry(d).update(mode=[]), "mode must be wireframe"),
            (lambda d: self.entry(d).update(flowId=[]), "flowId must be kebab-case"),
            (lambda d: self.entry(d).update(journeyId=[]), "not in reference.json"),
        ):
            with self.subTest(fragment=fragment):
                found = self.check(mutate)
                self.assertTrue(mentions(found, fragment))

    def test_malformed_reference_and_flow_members_return_errors(self):
        reference = copy.deepcopy(self.reference)
        reference["journeys"] = None
        found = adaptation.validate(copy.deepcopy(self.adaptation), reference, self.flow)
        self.assertTrue(mentions(found, "reference.journeys must be an array"))

        flow = copy.deepcopy(self.flow)
        flow["flows"] = [None]
        found = adaptation.validate(copy.deepcopy(self.adaptation), self.reference, flow)
        self.assertTrue(mentions(found, "flow.json.flows[0] must be an object"))

    def test_non_object_inputs_are_controlled_errors(self):
        self.assertEqual(
            adaptation.validate([], self.reference, self.flow),
            ["All three inputs must be JSON objects."],
        )


class ResearchGapsReachTheRoom(unittest.TestCase):
    """An assumption recorded only in adaptation.json is one nobody in the meeting sees."""

    def setUp(self):
        self.adaptation = load(FIXTURES / "adaptation.json")
        self.reference = load(FIXTURES / "reference.json")
        self.flow = load(FIXTURES / "flow.json")

    def check(self, mutate_flow=None, mutate_reference=None):
        flow = copy.deepcopy(self.flow)
        reference = copy.deepcopy(self.reference)
        if mutate_flow:
            mutate_flow(flow)
        if mutate_reference:
            mutate_reference(reference)
        return adaptation.validate(copy.deepcopy(self.adaptation), reference, flow)

    def flow_by_id(self, spec, flow_id):
        return next(item for item in spec["flows"] if item["id"] == flow_id)

    def test_a_partial_journey_needs_an_unsettled_review_point(self):
        # plan-comparison is derived from a partial journey.
        def mutate(spec):
            for item in self.flow_by_id(spec, "plan-comparison")["review"]:
                if item["status"] in ("open", "assumed"):
                    item["status"] = "confirmed"

        found = self.check(mutate_flow=mutate)
        self.assertTrue(mentions(found, "adapts a partial journey, but every review point",
                                 "facilitator walkthrough"))

    def test_an_observed_journey_may_settle_everything(self):
        # billing-questions is derived from a fully observed journey and is settled.
        self.assertEqual(self.check(), [])

    def test_an_observed_entry_must_cite_evidence_the_research_holds(self):
        def mutate(spec):
            self.flow_by_id(spec, "billing-questions")["entry"]["evidence"] = ["ev-invented"]

        found = self.check(mutate_flow=mutate)
        self.assertTrue(mentions(found, "cites evidence 'ev-invented'", "reference.json does not record"))

    def test_an_observed_entry_needs_evidence_at_all(self):
        def mutate(spec):
            del self.flow_by_id(spec, "billing-questions")["entry"]["evidence"]

        found = self.check(mutate_flow=mutate)
        self.assertTrue(mentions(found, "entry claims to be observed but cites no evidence ids"))

    def test_the_prototype_cannot_be_more_certain_than_the_research(self):
        def mutate(reference):
            for journey in reference["journeys"]:
                if journey["id"] == "journey-open-faq":
                    journey["entry"]["status"] = "inferred"

        found = self.check(mutate_reference=mutate)
        self.assertTrue(mentions(found, "cannot be more certain than the research"))

    def test_an_inferred_journey_may_not_yield_an_observed_entry(self):
        def mutate(reference):
            for journey in reference["journeys"]:
                if journey["id"] == "journey-open-faq":
                    journey["status"] = "inferred"

        found = self.check(mutate_reference=mutate)
        self.assertTrue(mentions(found, "the journey is inferred", "cannot claim basis 'observed'"))


if __name__ == "__main__":
    unittest.main()
