"""Rules for reference.json, the website research artifact."""

import copy
import json
import unittest

from _support import ROOT, mentions, reference

REFERENCE_DIR = ROOT / "tests" / "fixtures"


class ReferenceCase(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((REFERENCE_DIR / "reference.json").read_text(encoding="utf-8"))

    def check(self, mutate=None, base_dir=REFERENCE_DIR):
        payload = copy.deepcopy(self.data)
        if mutate:
            mutate(payload)
        return reference.validate(payload, base_dir)

    def journey(self, data, index=0):
        return data["journeys"][index]


class ReferenceRules(ReferenceCase):
    def test_fixture_is_valid(self):
        self.assertEqual(self.check(), [])

    def test_invalid_version_is_rejected(self):
        self.assertTrue(mentions(self.check(lambda d: d.update(version=99)),
                                 "version must equal 1"))
        self.assertTrue(mentions(self.check(lambda d: d.update(version=True)),
                                 "version must equal 1"))

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

    def test_limitations_must_be_recorded(self):
        self.assertTrue(mentions(self.check(lambda d: d.update(limitations=[])), "limitations must contain"))

    def test_source_url_must_be_http(self):
        def mutate(data):
            data["source"]["url"] = "file:///tmp/page.html"

        self.assertTrue(mentions(self.check(mutate), "must be an http(s) URL"))

    def test_viewport_objects_need_name_and_positive_dimensions(self):
        def mutate(data):
            data["coverage"]["viewports"] = [{}]

        found = self.check(mutate)
        for field in ("name", "width", "height"):
            with self.subTest(field=field):
                self.assertTrue(mentions(found, f"viewports[0].{field}"))

    def test_viewport_members_must_be_objects(self):
        found = self.check(lambda d: d["coverage"].update(viewports=[None]))
        self.assertTrue(mentions(found, "viewports[0] must be an object"))

    def test_viewport_names_must_be_unique(self):
        def mutate(data):
            data["coverage"]["viewports"].append({"name": "desktop", "width": 1440, "height": 1000})

        self.assertTrue(mentions(self.check(mutate), "Duplicate viewport id: desktop"))

    def test_evidence_viewport_must_be_declared(self):
        found = self.check(lambda d: d["evidence"][0].update(viewport="mobile"))
        self.assertTrue(mentions(found, "unknown viewport", "coverage.viewports"))

    def test_evidence_observation_and_journey_ids_must_be_unique(self):
        def mutate(data):
            data["evidence"].append(copy.deepcopy(data["evidence"][0]))
            data["observations"].append(copy.deepcopy(data["observations"][0]))
            data["journeys"].append(copy.deepcopy(data["journeys"][0]))

        found = self.check(mutate)
        for fragment in ("Duplicate evidence id", "Duplicate observation id", "Duplicate journey id"):
            with self.subTest(fragment=fragment):
                self.assertTrue(mentions(found, fragment))

    def test_observations_need_evidence_for_each_certainty_kind(self):
        for kind in ("observed", "inferred"):
            with self.subTest(kind=kind):
                def mutate(data, selected=kind):
                    data["observations"][0]["kind"] = selected
                    data["observations"][0]["evidence"] = []

                found = self.check(mutate)
                self.assertTrue(mentions(found, "Observation obs-plan-cards", "cites no evidence"))

    def test_screenshot_path_must_stay_inside_reference_directory(self):
        for path in ("../AGENTS.md", "..\\AGENTS.md", "C:\\Windows\\system.ini"):
            with self.subTest(path=path):
                def mutate(data, selected=path):
                    data["evidence"].append({
                        "id": "ev-outside-shot",
                        "kind": "screenshot",
                        "method": "browser",
                        "path": selected,
                        "url": data["source"]["url"],
                        "capturedAt": data["source"]["capturedAt"],
                        "viewport": "desktop",
                    })

                self.assertTrue(mentions(self.check(mutate), "relative to the reference directory"))

    def test_malformed_root_and_member_shapes_return_errors(self):
        self.assertTrue(mentions(reference.validate(None), "Reference must be a JSON object"))
        cases = [
            (lambda d: d.update(source=[]), "source must be an object"),
            (lambda d: d.update(coverage=[]), "coverage must include at least one viewport"),
            (lambda d: d.update(evidence=[None]), "Evidence record at index 0"),
            (lambda d: d.update(observations=[None]), "Observation at index 0"),
            (lambda d: d.update(journeys=[None]), "Journey at index 0"),
            (lambda d: d.update(limitations=[{}]), "limitations must contain"),
        ]
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                found = self.check(mutate)
                self.assertIsInstance(found, list)
                self.assertTrue(mentions(found, expected))

    def test_unhashable_member_values_are_reported_not_raised(self):
        def mutate(data):
            data["observations"][0]["kind"] = []
            data["evidence"][0]["viewport"] = []

        found = self.check(mutate)
        self.assertIsInstance(found, list)
        self.assertTrue(mentions(found, "must be observed or inferred"))
        self.assertTrue(mentions(found, "unknown viewport"))

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

        self.assertTrue(mentions(self.check(mutate), "points at a missing file"))

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


class JourneyEvidenceChain(ReferenceCase):
    """One screenshot of a page is not evidence that its buttons go anywhere."""

    def test_journey_status_is_constrained(self):
        def mutate(data):
            self.journey(data)["status"] = "probably"

        self.assertTrue(mentions(self.check(mutate), "needs a status of"))

    def test_journey_needs_at_least_two_steps(self):
        def mutate(data):
            self.journey(data)["steps"] = self.journey(data)["steps"][:1]

        self.assertTrue(mentions(self.check(mutate), "at least two steps"))

    def test_a_journey_needs_an_entry_declaration(self):
        # The prototype's own starting point is derived from this field.
        self.assertTrue(mentions(self.check(lambda d: self.journey(d).pop("entry")),
                                 "needs an 'entry' object"))

    def test_an_observed_entry_must_cite_evidence(self):
        def mutate(data):
            self.journey(data)["entry"]["evidence"] = []

        self.assertTrue(mentions(self.check(mutate), "entry is marked observed but cites no evidence"))

    def test_a_step_must_say_where_it_led(self):
        for field in ("action", "destination", "outcome"):
            with self.subTest(field=field):
                found = self.check(lambda d, f=field: self.journey(d)["steps"][0].update({f: ""}))
                self.assertTrue(mentions(found, f"steps[0] is missing {field}"))

    def test_a_step_may_not_be_a_bare_string(self):
        def mutate(data):
            self.journey(data)["steps"][0] = "Open the pricing page"

        self.assertTrue(mentions(self.check(mutate), "must be an object with action"))

    def test_an_observed_step_must_cite_evidence(self):
        def mutate(data):
            self.journey(data)["steps"][0]["evidence"] = []

        self.assertTrue(mentions(self.check(mutate), "Seeing a control is not seeing where it goes"))

    def test_evidence_kind_must_come_from_the_contract_allowlist(self):
        found = self.check(
            lambda data: data["evidence"][0].update({"kind": "made-up-proof"})
        )
        self.assertTrue(mentions(found, "unsupported kind", "made-up-proof"))

    def test_an_observed_interaction_step_cannot_rely_on_screenshots_only(self):
        def mutate(data):
            evidence = data["evidence"][0]
            evidence["kind"] = "screenshot"
            evidence["path"] = "screenshots/pricing.png"

        found = self.check(mutate, base_dir=None)
        self.assertTrue(
            mentions(
                found,
                "Journey journey-compare-plans.steps[0]",
                "interaction or navigation action",
                "only screenshot evidence",
            )
        )

    def test_passive_inspection_step_may_use_screenshot_only(self):
        def mutate(data):
            evidence = data["evidence"][0]
            evidence["kind"] = "screenshot"
            evidence["path"] = "screenshots/pricing.png"
            for journey in data["journeys"]:
                for step in journey["steps"]:
                    step["action"] = "Inspect the current page"

        self.assertEqual(self.check(mutate, base_dir=None), [])

    def test_entry_evidence_array_is_required_for_partial_and_inferred_claims(self):
        for status in ("partial", "inferred"):
            with self.subTest(status=status):
                def mutate(data, selected=status):
                    entry = self.journey(data)["entry"]
                    entry["status"] = selected
                    entry.pop("evidence", None)

                found = self.check(mutate)
                self.assertTrue(mentions(found, ".entry.evidence is required"))

    def test_every_step_needs_an_evidence_array(self):
        for status in ("observed", "partial", "inferred"):
            with self.subTest(status=status):
                def mutate(data, selected=status):
                    step = self.journey(data)["steps"][0]
                    step["status"] = selected
                    step.pop("evidence", None)

                found = self.check(mutate)
                self.assertTrue(mentions(found, "steps[0].evidence is required"))

    def test_partial_entry_and_step_need_non_empty_evidence(self):
        def mutate(data):
            journey = self.journey(data)
            journey["entry"]["status"] = "partial"
            journey["entry"]["evidence"] = []
            journey["steps"][0]["status"] = "partial"
            journey["steps"][0]["evidence"] = []

        found = self.check(mutate)
        self.assertTrue(mentions(found, "entry is marked partial"))
        self.assertTrue(mentions(found, "steps[0] is marked partial"))

    def test_inferred_step_may_explicitly_record_no_direct_evidence(self):
        # This is the fixture's documented research gap and must remain valid.
        self.assertEqual(self.check(), [])

    def test_a_step_may_not_cite_unknown_evidence(self):
        def mutate(data):
            self.journey(data)["steps"][0]["evidence"] = ["ev-imaginary"]

        self.assertTrue(mentions(self.check(mutate), "cites unknown evidence ev-imaginary"))

    def test_a_journey_is_only_as_observed_as_its_weakest_link(self):
        # The fixture's first journey has one inferred step and calls itself partial.
        def mutate(data):
            self.journey(data)["status"] = "observed"

        self.assertTrue(mentions(self.check(mutate), "claims status 'observed'", "1 of its links are not"))

    def test_an_unobserved_entry_also_breaks_the_chain(self):
        def mutate(data):
            journey = self.journey(data, 1)
            journey["entry"]["status"] = "inferred"
            journey["entry"]["evidence"] = []

        self.assertTrue(mentions(self.check(mutate), "claims status 'observed'", "of its links are not"))

    def test_a_fully_observed_journey_passes(self):
        # The fixture's second journey is observed end to end.
        self.assertEqual(self.check(), [])


if __name__ == "__main__":
    unittest.main()
