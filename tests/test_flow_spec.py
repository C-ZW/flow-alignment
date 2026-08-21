"""Graph-level rules for flow.json.

Each test introduces exactly one defect into a known-good specification and
asserts the validator names it.
"""

import unittest

from _support import check_spec, mentions, valid_spec, flow_spec, warnings


def only_flow(spec):
    return spec["flows"][0]


def state(spec, state_id):
    return next(item for item in only_flow(spec)["states"] if item["id"] == state_id)


class DocumentRules(unittest.TestCase):
    def test_shipped_template_specification_is_valid(self):
        self.assertEqual(check_spec(valid_spec()), [])

    def test_version_one_is_rejected_with_migration_guidance(self):
        spec = valid_spec()
        spec["version"] = 1
        self.assertTrue(mentions(check_spec(spec), "retired version 1", "flows"))

    def test_unknown_version_is_rejected(self):
        spec = valid_spec()
        spec["version"] = 99
        self.assertTrue(mentions(check_spec(spec), "version must equal 2"))

    def test_flows_array_is_required(self):
        spec = valid_spec()
        spec["flows"] = []
        self.assertTrue(mentions(check_spec(spec), "non-empty 'flows' array"))

    def test_duplicate_flow_ids_are_rejected(self):
        spec = valid_spec()
        spec["flows"].append(dict(only_flow(spec)))
        self.assertTrue(mentions(check_spec(spec), "Duplicate flow id"))

    def test_more_than_three_flows_warns_but_passes(self):
        spec = valid_spec()
        for index in range(3):
            extra = dict(only_flow(spec))
            extra["id"] = f"extra-flow-{index}"
            spec["flows"].append(extra)
        issues, _ = flow_spec.validate_spec(spec)
        self.assertEqual(check_spec(spec), [])
        self.assertTrue(mentions(warnings(issues), "one focused hypothesis"))


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

    def test_error_simulation_requires_a_label(self):
        spec = valid_spec()
        only_flow(spec)["errorSimulation"] = {"supported": True, "label": ""}
        self.assertTrue(mentions(check_spec(spec), "error simulation", "no label"))

    def test_error_simulation_may_be_disabled(self):
        spec = valid_spec()
        only_flow(spec)["errorSimulation"] = {"supported": False, "label": ""}
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
        duplicate = dict(state(spec, "done"))
        only_flow(spec)["states"].append(duplicate)
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

    def test_initial_state_must_exist(self):
        spec = valid_spec()
        only_flow(spec)["initialState"] = "missing"
        self.assertTrue(mentions(check_spec(spec), "initialState must reference a declared state"))

    def test_a_terminal_state_is_required(self):
        spec = valid_spec()
        for state_id in ("done", "declined"):
            del state(spec, state_id)["terminal"]
        self.assertTrue(mentions(check_spec(spec), "at least one state marked terminal"))

    def test_terminal_state_must_be_reachable(self):
        spec = valid_spec()
        # Cut the only paths into the terminal states.
        state(spec, "decision")["transitions"] = ["record-list"]
        found = check_spec(spec)
        self.assertTrue(mentions(found, "'done' is unreachable"))
        self.assertTrue(mentions(found, "no terminal state reachable"))

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
        state(spec, "app-home")["transitions"] = ["record-list"]
        issues, _ = flow_spec.validate_spec(spec)
        self.assertTrue(mentions(warnings(issues), "opens the whole shell but offers no navTargets"))

    def test_initial_state_off_step_one_is_only_a_warning(self):
        spec = valid_spec()
        state(spec, "app-home")["step"] = 2
        issues, _ = flow_spec.validate_spec(spec)
        self.assertEqual(check_spec(spec), [])
        self.assertTrue(mentions(warnings(issues), "initialState is not step 1"))


if __name__ == "__main__":
    unittest.main()
