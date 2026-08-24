"""Graph-level rules for flow.json.

Each test introduces exactly one defect into a known-good specification and
asserts the validator names it. The known-good specification is the one embedded
in the shipped template, so these tests fail the moment the template drifts from
the contract.
"""

import copy
import unittest

from _support import check_html, check_spec, mentions, template_html, valid_spec, flow_spec, warnings


def only_flow(spec):
    return spec["flows"][0]


def state(spec, state_id):
    return next(item for item in only_flow(spec)["states"] if item["id"] == state_id)


def review(spec, aspect):
    return next(item for item in only_flow(spec)["review"] if item["aspect"] == aspect)


def drop_state(spec, state_id):
    """Remove a state and every transition into it."""
    only_flow(spec)["states"] = [s for s in only_flow(spec)["states"] if s["id"] != state_id]
    for item in only_flow(spec)["states"]:
        item["transitions"] = [t for t in item["transitions"] if t != state_id]


class DocumentRules(unittest.TestCase):
    def test_shipped_template_specification_is_valid(self):
        self.assertEqual(check_spec(valid_spec()), [])

    def test_invalid_version_is_rejected(self):
        spec = valid_spec()
        spec["version"] = 99
        self.assertTrue(mentions(check_spec(spec), "version must equal 1"))

    def test_boolean_is_not_version_one(self):
        spec = valid_spec()
        spec["version"] = True
        self.assertTrue(mentions(check_spec(spec), "version must equal 1"))

    def test_flows_array_is_required(self):
        spec = valid_spec()
        spec["flows"] = []
        self.assertTrue(mentions(check_spec(spec), "non-empty 'flows' array"))

    def test_script_closing_text_is_rejected_before_embedding(self):
        spec = valid_spec()
        only_flow(spec)["task"] = "Unsafe </script><script>alert(1)</script>"
        self.assertTrue(mentions(check_spec(spec), "would break or inject markup"))

    def test_duplicate_flow_ids_are_rejected(self):
        spec = valid_spec()
        spec["flows"].append(dict(only_flow(spec)))
        self.assertTrue(mentions(check_spec(spec), "Duplicate flow id"))

    def test_more_than_three_flows_is_rejected(self):
        spec = valid_spec()
        for index in range(3):
            extra = dict(only_flow(spec))
            extra["id"] = f"extra-flow-{index}"
            spec["flows"].append(extra)
        self.assertTrue(mentions(check_spec(spec), "at most three related journeys"))

    def test_non_object_root_is_rejected_without_an_exception(self):
        for malformed in (None, [], "flow"):
            with self.subTest(root=malformed):
                self.assertTrue(mentions(check_spec(malformed), "flow.json must be a JSON object"))


class FlowRules(unittest.TestCase):
    def test_task_is_required(self):
        spec = valid_spec()
        only_flow(spec)["task"] = "   "
        self.assertTrue(mentions(check_spec(spec), "missing task"))

    def test_research_fields_are_optional(self):
        # A flow being confirmed with a client has a scenario, not a hypothesis.
        spec = valid_spec()
        only_flow(spec).pop("hypothesis", None)
        only_flow(spec).pop("successSignal", None)
        self.assertEqual(check_spec(spec), [])

    def test_an_empty_research_field_is_rejected(self):
        for field in ("hypothesis", "successSignal"):
            with self.subTest(field=field):
                spec = valid_spec()
                only_flow(spec)[field] = "   "
                self.assertTrue(mentions(check_spec(spec), f"empty {field}"))

    def test_flow_id_must_be_kebab_case(self):
        spec = valid_spec()
        only_flow(spec)["id"] = "Sample Flow"
        self.assertTrue(mentions(check_spec(spec), "id must be a kebab-case string"))


class EntryRules(unittest.TestCase):
    """Where the journey starts, and on whose authority."""

    def test_entry_is_required(self):
        spec = valid_spec()
        del only_flow(spec)["entry"]
        self.assertTrue(mentions(check_spec(spec), "needs an 'entry' object"))

    def test_entry_state_must_exist(self):
        spec = valid_spec()
        only_flow(spec)["entry"]["state"] = "missing"
        self.assertTrue(mentions(check_spec(spec), "entry.state must reference a declared state"))

    def test_entry_state_must_be_step_one(self):
        # The rule the artifact exists to serve: start at the beginning.
        spec = valid_spec()
        state(spec, "app-home")["step"] = 2
        self.assertTrue(mentions(check_spec(spec), "is not step 1", "start at the beginning"))

    def test_entry_state_may_not_be_terminal(self):
        spec = valid_spec()
        state(spec, "app-home")["terminal"] = True
        self.assertTrue(mentions(check_spec(spec), "'app-home' is also terminal"))

    def test_entry_basis_is_constrained(self):
        spec = valid_spec()
        only_flow(spec)["entry"]["basis"] = "obviously"
        self.assertTrue(mentions(check_spec(spec), "entry.basis must be one of"))

    def test_an_observed_entry_must_cite_evidence(self):
        spec = valid_spec()
        only_flow(spec)["entry"]["basis"] = "observed"
        self.assertTrue(mentions(check_spec(spec), "observed but cites no evidence"))

    def test_an_observed_entry_with_evidence_passes(self):
        spec = valid_spec()
        only_flow(spec)["entry"]["basis"] = "observed"
        only_flow(spec)["entry"]["evidence"] = ["ev-home"]
        review(spec, "entry-point")["status"] = "confirmed"
        del review(spec, "entry-point")["question"]
        self.assertEqual(check_spec(spec), [])

    def test_entry_needs_a_reason(self):
        spec = valid_spec()
        only_flow(spec)["entry"]["why"] = ""
        self.assertTrue(mentions(check_spec(spec), "entry.why must say why"))

    def test_preconditions_must_be_declared(self):
        spec = valid_spec()
        del only_flow(spec)["entry"]["preconditions"]
        self.assertTrue(mentions(check_spec(spec), "preconditions must be an array"))

    def test_empty_preconditions_only_warns(self):
        # Stating "there are none" is a decision; omitting the field is not.
        spec = valid_spec()
        only_flow(spec)["entry"]["preconditions"] = []
        issues, _ = flow_spec.validate_spec(spec)
        self.assertEqual(check_spec(spec), [])
        self.assertTrue(mentions(warnings(issues), "declares no preconditions"))


class FocusRules(unittest.TestCase):
    """Which screens the meeting is actually about."""

    def test_focus_is_required(self):
        spec = valid_spec()
        del only_flow(spec)["focus"]
        self.assertTrue(mentions(check_spec(spec), "needs a non-empty 'focus' array"))

    def test_focus_may_not_be_the_entry_state(self):
        # Opening on the screen under discussion is what this field prevents.
        spec = valid_spec()
        only_flow(spec)["focus"] = ["app-home"]
        self.assertTrue(mentions(check_spec(spec), "also the entry point"))

    def test_focus_must_name_a_declared_state(self):
        spec = valid_spec()
        only_flow(spec)["focus"] = ["imaginary"]
        self.assertTrue(mentions(check_spec(spec), "focus names undeclared state 'imaginary'"))

    def test_focus_must_be_reachable_by_walking(self):
        spec = valid_spec()
        state(spec, "record-list")["transitions"] = ["app-home"]
        found = check_spec(spec)
        self.assertTrue(mentions(found, "focus names 'decision'", "cannot be reached from the entry point"))

    def test_duplicate_focus_entries_are_rejected(self):
        spec = valid_spec()
        only_flow(spec)["focus"] = ["decision", "decision"]
        self.assertTrue(mentions(check_spec(spec), "focus lists the same state twice"))


class SpotlightRules(unittest.TestCase):
    """Which product region remains usable on each screen."""

    def test_missing_spotlight_warns_about_whole_viewport_fallback(self):
        spec = valid_spec()
        del state(spec, "decision")["spotlight"]
        issues, _ = flow_spec.validate_spec(spec)
        self.assertEqual(check_spec(spec), [])
        self.assertTrue(mentions(warnings(issues), "mask falls back to the whole viewport"))

    def test_spotlight_is_a_stable_region_key(self):
        spec = valid_spec()
        state(spec, "decision")["spotlight"] = "Decision Actions"
        self.assertTrue(mentions(check_spec(spec), "spotlight must be a kebab-case region key"))

    def test_two_or_three_separate_spotlight_regions_are_allowed(self):
        spec = valid_spec()
        decision = state(spec, "decision")
        del decision["spotlight"]
        decision["spotlights"] = ["decision-context", "decision-actions"]
        self.assertEqual(check_spec(spec), [])

    def test_singular_and_plural_spotlight_fields_are_mutually_exclusive(self):
        spec = valid_spec()
        state(spec, "decision")["spotlights"] = ["decision-context", "decision-actions"]
        self.assertTrue(mentions(check_spec(spec), "use spotlight or spotlights, not both"))

    def test_multi_region_spotlights_are_bounded_unique_keys(self):
        for keys, message in ((["one"], "two or three"),
                              (["one", "one"], "must not repeat"),
                              (["one", "two", "three", "four"], "two or three"),
                              (["one", "Not Stable"], "kebab-case")):
            with self.subTest(keys=keys):
                spec = valid_spec()
                decision = state(spec, "decision")
                del decision["spotlight"]
                decision["spotlights"] = keys
                self.assertTrue(mentions(check_spec(spec), message))


class ResponsiveAlternativeRules(unittest.TestCase):
    """A breakpoint-specific action graph is another journey, not hidden setup."""

    def add_mobile_flow(self, spec):
        mobile = copy.deepcopy(only_flow(spec))
        mobile["id"] = "sample-flow-mobile"
        spec["flows"].append(mobile)

    def test_a_built_responsive_alternative_passes(self):
        spec = valid_spec()
        self.add_mobile_flow(spec)
        only_flow(spec)["responsiveAlternatives"] = [{
            "flowId": "sample-flow-mobile",
            "viewport": "narrow",
            "reason": "Narrow navigation requires an extra menu step.",
        }]
        self.assertEqual(check_spec(spec), [])

    def test_responsive_alternative_must_name_a_built_distinct_flow(self):
        for flow_id, message in (("sample-flow", "may not name its own flow"),
                                 ("missing-mobile", "is not built")):
            with self.subTest(flow_id=flow_id):
                spec = valid_spec()
                only_flow(spec)["responsiveAlternatives"] = [{
                    "flowId": flow_id, "viewport": "narrow", "reason": "The graph changes."
                }]
                self.assertTrue(mentions(check_spec(spec), message))

    def test_responsive_alternative_needs_viewport_and_reason(self):
        spec = valid_spec()
        self.add_mobile_flow(spec)
        only_flow(spec)["responsiveAlternatives"] = [{
            "flowId": "sample-flow-mobile", "viewport": "tablet", "reason": ""
        }]
        found = check_spec(spec)
        self.assertTrue(mentions(found, "viewport must be narrow or wide"))
        self.assertTrue(mentions(found, "reason must say why"))


class ReviewLedgerRules(unittest.TestCase):
    """Silence reads as agreement, so the ledger cannot be silent."""

    def test_review_is_required(self):
        spec = valid_spec()
        del only_flow(spec)["review"]
        self.assertTrue(mentions(check_spec(spec), "needs a 'review' array"))

    def test_every_aspect_must_be_addressed(self):
        for aspect in ("entry-point", "navigation", "branches", "failure-recovery", "ending-state"):
            with self.subTest(aspect=aspect):
                spec = valid_spec()
                only_flow(spec)["review"] = [
                    item for item in only_flow(spec)["review"] if item["aspect"] != aspect
                ]
                self.assertTrue(mentions(check_spec(spec), f"says nothing about '{aspect}'"))

    def test_open_is_a_valid_position(self):
        # The whole point: an unanswered question must not fail validation.
        spec = valid_spec()
        for item in only_flow(spec)["review"]:
            item["status"] = "open"
            item.setdefault("question", "What should this do?")
            item.setdefault("states", ["decision"])
            if not item["states"]:
                item["states"] = ["decision"]
        self.assertEqual(check_spec(spec), [])

    def test_status_is_constrained(self):
        spec = valid_spec()
        review(spec, "branches")["status"] = "probably-fine"
        self.assertTrue(mentions(check_spec(spec), "status must be one of"))

    def test_duplicate_aspects_are_rejected(self):
        spec = valid_spec()
        only_flow(spec)["review"].append(dict(review(spec, "branches")))
        self.assertTrue(mentions(check_spec(spec), "declares 'branches' twice"))

    def test_unknown_aspect_is_rejected(self):
        spec = valid_spec()
        review(spec, "branches")["aspect"] = "vibes"
        self.assertTrue(mentions(check_spec(spec), "has aspect 'vibes'"))

    def test_a_proposal_is_required(self):
        spec = valid_spec()
        review(spec, "branches")["proposal"] = ""
        self.assertTrue(mentions(check_spec(spec), "proposal must state what this artifact currently proposes"))

    def test_an_unsettled_point_must_ask_something(self):
        for status in ("open", "assumed"):
            with self.subTest(status=status):
                spec = valid_spec()
                review(spec, "branches")["status"] = status
                review(spec, "branches").pop("question", None)
                self.assertTrue(mentions(check_spec(spec), f"is {status} but asks nothing"))

    def test_a_point_must_be_attached_to_screens(self):
        # A point with no states cannot be placed at the right moment in the walkthrough.
        spec = valid_spec()
        review(spec, "branches")["states"] = []
        self.assertTrue(mentions(check_spec(spec), "names no states"))

    def test_a_not_applicable_point_may_name_no_screens(self):
        spec = valid_spec()
        point = review(spec, "failure-recovery")
        point.update(status="not-applicable", states=[], proposal="Nothing here can fail.")
        point.pop("question", None)
        self.assertEqual(check_spec(spec), [])

    def test_a_point_must_name_declared_states(self):
        spec = valid_spec()
        review(spec, "branches")["states"] = ["ghost-screen"]
        self.assertTrue(mentions(check_spec(spec), "names undeclared state 'ghost-screen'"))

    def test_the_ledger_may_not_contradict_the_entry_declaration(self):
        spec = valid_spec()
        point = review(spec, "entry-point")
        point["status"] = "confirmed"
        point.pop("question", None)
        self.assertTrue(mentions(check_spec(spec), "confirmed while entry.basis is 'assumed'"))

    def test_failure_recovery_may_reference_a_separate_failure_flow(self):
        spec = valid_spec()
        point = review(spec, "failure-recovery")
        point.update(status="confirmed", states=["decision"])
        point.pop("question", None)
        self.assertEqual(check_spec(spec), [])

    def test_everything_confirmed_only_warns(self):
        spec = valid_spec()
        for item in only_flow(spec)["review"]:
            item["status"] = "confirmed"
            item.pop("question", None)
            if not item["states"]:
                item["states"] = ["decision"]
        only_flow(spec)["entry"]["basis"] = "provided"
        issues, _ = flow_spec.validate_spec(spec)
        self.assertEqual(check_spec(spec), [])
        self.assertTrue(mentions(warnings(issues), "If nothing is open, what is the walkthrough for?"))

    def test_a_design_alternative_must_be_a_flow_this_artifact_builds(self):
        spec = valid_spec()
        review(spec, "branches")["alternativeFlows"] = ["defer-and-remind"]
        self.assertTrue(mentions(check_spec(spec), "names alternative flow 'defer-and-remind'",
                                 "this artifact does not build"))

    def test_a_design_alternative_may_not_name_its_own_flow(self):
        spec = valid_spec()
        review(spec, "branches")["alternativeFlows"] = ["sample-flow"]
        self.assertTrue(mentions(check_spec(spec), "names itself as the alternative"))

    def test_a_built_design_alternative_passes(self):
        spec = valid_spec()
        other = copy.deepcopy(only_flow(spec))
        other["id"] = "sample-flow-alternative"
        spec["flows"].append(other)
        review(spec, "branches")["alternativeFlows"] = ["sample-flow-alternative"]
        self.assertEqual(check_spec(spec), [])


class StateRules(unittest.TestCase):
    def test_at_least_two_states(self):
        spec = valid_spec()
        only_flow(spec)["states"] = only_flow(spec)["states"][:1]
        self.assertTrue(mentions(check_spec(spec), "at least two states"))

    def test_state_id_must_be_kebab_case(self):
        spec = valid_spec()
        state(spec, "done")["id"] = "Done_State"
        self.assertTrue(mentions(check_spec(spec), "without a kebab-case id"))

    def test_duplicate_state_ids_are_rejected(self):
        spec = valid_spec()
        only_flow(spec)["states"].append(dict(state(spec, "done")))
        self.assertTrue(mentions(check_spec(spec), "duplicate state id", "done"))

    def test_step_must_be_a_positive_integer(self):
        for bad_step in (0, -1, "2", 1.5, True):
            with self.subTest(step=bad_step):
                spec = valid_spec()
                state(spec, "decision")["step"] = bad_step
                self.assertTrue(mentions(check_spec(spec), "positive integer step"))

    def test_instruction_is_required(self):
        spec = valid_spec()
        state(spec, "decision")["instruction"] = ""
        self.assertTrue(mentions(check_spec(spec), "missing instruction"))

    def test_transition_to_unknown_state_is_rejected(self):
        spec = valid_spec()
        state(spec, "app-home")["transitions"] = ["nowhere"]
        state(spec, "app-home")["navTargets"] = {"records": "nowhere"}
        self.assertTrue(mentions(check_spec(spec), "unknown state 'nowhere'"))

    def test_duplicate_transition_is_rejected(self):
        spec = valid_spec()
        state(spec, "decision")["transitions"] = ["done", "done"]
        self.assertTrue(mentions(check_spec(spec), "duplicate transition"))

    def test_unreachable_state_is_rejected(self):
        spec = valid_spec()
        state(spec, "app-home")["transitions"] = []
        found = check_spec(spec)
        self.assertTrue(mentions(found, "'record-list' is unreachable"))
        self.assertTrue(mentions(found, "'decision' is unreachable"))

    def test_a_terminal_state_is_required(self):
        spec = valid_spec()
        for state_id in ("done", "declined"):
            del state(spec, state_id)["terminal"]
        self.assertTrue(mentions(check_spec(spec), "at least one state marked terminal"))

    def test_a_reachable_closed_loop_cannot_hide_beside_a_terminal_branch(self):
        spec = valid_spec()
        flow = only_flow(spec)
        flow["states"].append({
            "id": "dead-loop",
            "title": "Closed loop",
            "step": 2,
            "instruction": "This branch never reaches an outcome.",
            "transitions": ["dead-loop"],
            "spotlight": "loop-region",
        })
        state(spec, "app-home")["transitions"].append("dead-loop")
        found = check_spec(spec)
        self.assertTrue(mentions(
            found,
            "'dead-loop'",
            "cannot reach a valid terminal outcome",
            "closed loop",
        ))

    def test_a_dead_end_is_rejected(self):
        spec = valid_spec()
        state(spec, "record-list")["transitions"] = []
        self.assertTrue(mentions(check_spec(spec), "'record-list' is a dead end"))

    def test_nav_must_route_to_a_declared_transition(self):
        spec = valid_spec()
        state(spec, "app-home")["navTargets"] = {"records": "done"}
        self.assertTrue(mentions(check_spec(spec), "routes nav 'records' to 'done'", "not a declared transition"))

    def test_nav_requires_shell_scope(self):
        spec = valid_spec()
        state(spec, "app-home")["scope"] = "viewport"
        self.assertTrue(mentions(check_spec(spec), "declares navTargets but not scope 'shell'"))

    def test_scope_is_constrained(self):
        spec = valid_spec()
        state(spec, "decision")["scope"] = "sidebar"
        self.assertTrue(mentions(check_spec(spec), "use viewport or shell"))

    def test_shell_scope_without_navigation_only_warns(self):
        spec = valid_spec()
        del state(spec, "app-home")["navTargets"]
        issues, _ = flow_spec.validate_spec(spec)
        self.assertTrue(mentions(warnings(issues), "opens the whole shell but offers no navTargets"))

    def test_navigation_only_shell_may_not_route_multiple_controls(self):
        spec = valid_spec()
        state(spec, "app-home")["navTargets"] = {
            "records": "record-list",
            "records-alternate": "record-list",
        }
        self.assertTrue(mentions(check_spec(spec), "at most one routed navigation control"))


class BranchSemantics(unittest.TestCase):
    """Steps that share a number are drawn as alternatives, so they must be."""

    def test_consecutive_screens_may_not_share_a_step_number(self):
        spec = valid_spec()
        state(spec, "record-list-updated")["step"] = 4
        self.assertTrue(mentions(check_spec(spec), "as alternatives at step 4",
                                 "'record-list-updated' follows 'done'"))

    def test_a_back_transition_does_not_make_two_screens_consecutive(self):
        # record-list can return to app-home; that is navigation, not sequence.
        spec = valid_spec()
        self.assertEqual(check_spec(spec), [])

    def test_a_fork_across_different_steps_only_warns(self):
        spec = valid_spec()
        state(spec, "declined")["step"] = 6
        state(spec, "record-list-unchanged")["step"] = 7
        issues, _ = flow_spec.validate_spec(spec)
        self.assertEqual(check_spec(spec), [])
        self.assertTrue(mentions(warnings(issues), "'decision' forks to", "different steps"))


class OutcomeRules(unittest.TestCase):
    """A terminal state has to say what its branch actually did."""

    def test_a_terminal_state_needs_an_outcome(self):
        spec = valid_spec()
        del state(spec, "done")["outcome"]
        self.assertTrue(mentions(check_spec(spec), "terminal state 'done' has no outcome"))

    def test_a_non_terminal_state_may_not_carry_one(self):
        spec = valid_spec()
        state(spec, "decision")["outcome"] = {"happened": "x", "changed": ["y"], "continuation": None}
        self.assertTrue(mentions(check_spec(spec), "declares an outcome but is not terminal"))

    def test_what_happened_is_required(self):
        spec = valid_spec()
        state(spec, "done")["outcome"]["happened"] = ""
        self.assertTrue(mentions(check_spec(spec), "is missing 'happened'"))

    def test_what_changed_is_required(self):
        spec = valid_spec()
        state(spec, "done")["outcome"]["changed"] = []
        self.assertTrue(mentions(check_spec(spec), "needs a non-empty 'changed' list"))

    def test_a_continuation_must_be_declared_even_when_null(self):
        spec = valid_spec()
        del state(spec, "done")["outcome"]["continuation"]
        self.assertTrue(mentions(check_spec(spec), "must declare a continuation, or null"))

    def test_a_null_continuation_requires_no_transitions(self):
        spec = valid_spec()
        state(spec, "done")["outcome"]["continuation"] = None
        self.assertTrue(mentions(check_spec(spec), "declares no continuation but the state still transitions"))

    def test_a_journey_may_genuinely_stop_at_the_outcome(self):
        spec = valid_spec()
        state(spec, "done")["outcome"]["continuation"] = None
        state(spec, "done")["transitions"] = []
        drop_state(spec, "record-list-updated")
        review(spec, "ending-state")["states"] = ["record-list-unchanged"]
        self.assertEqual(check_spec(spec), [])

    def test_a_continuation_must_be_a_declared_transition(self):
        spec = valid_spec()
        state(spec, "done")["outcome"]["continuation"] = "record-list-unchanged"
        self.assertTrue(mentions(check_spec(spec), "continues to 'record-list-unchanged'",
                                 "not a declared transition"))

    def test_a_continuation_may_not_be_a_screen_already_walked(self):
        # The engine is stateless, so a previously visited screen shows its pre-action state.
        spec = valid_spec()
        state(spec, "done")["transitions"] = ["record-list"]
        state(spec, "done")["outcome"]["continuation"] = "record-list"
        found = check_spec(spec)
        self.assertTrue(mentions(found, "a screen the walker already passed through"))

    def test_two_outcomes_may_not_share_one_continuation(self):
        spec = valid_spec()
        state(spec, "declined")["transitions"] = ["record-list-updated"]
        state(spec, "declined")["outcome"]["continuation"] = "record-list-updated"
        found = check_spec(spec)
        self.assertTrue(mentions(found, "One screen cannot show two different outcomes"))

    def test_a_non_null_continuation_must_be_the_only_terminal_transition(self):
        spec = valid_spec()
        state(spec, "done")["transitions"] = ["record-list-updated", "record-list"]
        found = check_spec(spec)
        self.assertTrue(mentions(found, "exactly one transition matching continuation"))


class MalformedMemberRules(unittest.TestCase):
    """Bad JSON member shapes report issues instead of leaking Python errors."""

    def test_entry_state_must_be_a_string(self):
        spec = valid_spec()
        only_flow(spec)["entry"]["state"] = []
        self.assertTrue(mentions(check_spec(spec), "entry.state must reference a declared state"))

    def test_focus_members_must_be_strings(self):
        spec = valid_spec()
        only_flow(spec)["focus"] = [["decision"]]
        self.assertTrue(mentions(check_spec(spec), "focus must contain only state id strings"))

    def test_review_members_must_be_strings(self):
        spec = valid_spec()
        review(spec, "branches")["status"] = []
        review(spec, "navigation")["states"] = [[]]
        found = check_spec(spec)
        self.assertTrue(mentions(found, "status must be one of"))
        self.assertTrue(mentions(found, "states must contain only state id strings"))

    def test_malformed_navigation_destination_is_reported_without_crashing(self):
        spec = valid_spec()
        state(spec, "app-home")["navTargets"] = {"records": []}
        self.assertTrue(mentions(check_spec(spec), "destination that is not a state id"))

    def test_malformed_responsive_alternative_is_reported_without_crashing(self):
        spec = valid_spec()
        only_flow(spec)["responsiveAlternatives"] = [{"flowId": [], "viewport": "narrow", "reason": "x"}]
        self.assertTrue(mentions(check_spec(spec), "flowId must be a flow id string"))


class OfflineRules(unittest.TestCase):
    def test_deceptive_font_host_is_not_allowlisted_by_substring(self):
        html = template_html().replace(
            "</body>",
            '<img src="https://attacker.example/fonts.googleapis.com/css"> </body>',
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "attacker.example", "not permitted"))

    def test_send_beacon_is_rejected(self):
        html = template_html().replace(
            "</body>",
            "<script>navigator.sendBeacon('/events')</script></body>",
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "must run offline"))

    def test_analytics_calls_are_rejected(self):
        html = template_html().replace(
            "</body>",
            "<script>analytics.track('state')</script></body>",
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "must run offline"))

    def test_remote_resources_in_css_and_less_common_attributes_are_rejected(self):
        probes = (
            '<style>.x{background:url("https://cdn.example/x.png")}</style>',
            '<style>@import "https://cdn.example/x.css";</style>',
            '<img srcset="https://cdn.example/x.png 2x">',
            '<iframe srcdoc="&lt;img src=https://cdn.example/x.png&gt;"></iframe>',
            '<object data="https://cdn.example/x.svg"></object>',
        )
        for probe in probes:
            with self.subTest(probe=probe):
                html = template_html().replace("</body>", probe + "</body>")
                found, _ = check_html(html)
                self.assertTrue(mentions(found, "cdn.example", "not permitted"))

    def test_remote_image_assignment_is_rejected(self):
        html = template_html().replace(
            "</body>",
            "<script>const beacon = new Image(); beacon.src = 'https://cdn.example/p.gif'</script></body>",
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "must run offline"))

    def test_product_css_text_may_not_drop_below_13px(self):
        html = template_html().replace(
            "</style>",
            ".tiny-product-label { font: 700 11px/1.2 sans-serif; }</style>",
            1,
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "11px text", "minimum is 13px"))

if __name__ == "__main__":
    unittest.main()
