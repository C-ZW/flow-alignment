"""External review record → plan → safe source update."""

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from _support import review_apply, template_html, valid_spec


def record(sequence, flow_id, state_id, aspect, decision="confirmed", note=""):
    return {
        "sequence": sequence,
        "recordedAt": f"2026-08-23T10:00:{sequence:02d}.000Z",
        "recordedBy": "Client PM",
        "flowId": flow_id,
        "flowTitle": "Sample flow",
        "stateId": state_id,
        "stateTitle": state_id,
        "stateStep": 1,
        "target": {"type": "review-item", "aspect": aspect},
        "decision": decision,
        "note": note,
        "review": [],
    }


def session(spec, records, drafts=None):
    flows = {flow["id"]: flow for flow in spec["flows"]}
    for item in records:
        target = item.get("target", {})
        if target.get("type") != "review-item" or item.get("review"):
            continue
        declared = next(
            point for point in flows[item["flowId"]]["review"]
            if point["aspect"] == target["aspect"]
        )
        item["review"] = [{
            "aspect": declared["aspect"],
            "declaredStatus": declared["status"],
            "proposal": declared["proposal"],
            "question": declared.get("question") or None,
            "alternatives": declared.get("alternatives") or [],
        }]
    return {
        "version": 1,
        "sessionId": "review-2026-08-23T10-00-00Z",
        "artifact": {
            "source": "embedded-flow-spec",
            "artifactId": "sample-flow",
            "revision": "fnv1a-rendered-document",
            "specRevision": review_apply.fnv1a(review_apply.compact_json(spec)),
            "specVersion": spec["version"],
            "specSnapshot": copy.deepcopy(spec),
        },
        "exportedAt": "2026-08-23T10:01:00.000Z",
        "records": records,
        "drafts": drafts or [],
    }


def only_flow(spec):
    return spec["flows"][0]


def review(spec, aspect):
    return next(item for item in only_flow(spec)["review"] if item["aspect"] == aspect)


class PlanRules(unittest.TestCase):
    def test_boolean_is_not_review_session_version_one(self):
        spec = valid_spec()
        payload = session(spec, [])
        payload["version"] = True
        self.assertIn("review session version must equal 1", review_apply.validate_session(payload))

    def test_every_attached_state_must_have_a_latest_confirmation(self):
        spec = valid_spec()
        flow_id = only_flow(spec)["id"]
        payload = session(spec, [record(1, flow_id, "app-home", "navigation")])
        plan = review_apply.build_plan(payload, spec, Path("prototype"))
        self.assertEqual(plan["safeConfirmations"], [])
        self.assertEqual(plan["summary"]["incompleteConfirmations"], 1)

    def test_all_attached_states_make_one_safe_confirmation(self):
        spec = valid_spec()
        flow_id = only_flow(spec)["id"]
        payload = session(spec, [
            record(1, flow_id, "app-home", "navigation"),
            record(2, flow_id, "record-list", "navigation"),
        ])
        plan = review_apply.build_plan(payload, spec, Path("prototype"))
        self.assertEqual(plan["blockers"], [])
        self.assertEqual(plan["safeConfirmations"][0]["aspect"], "navigation")

    def test_latest_decision_overrides_an_earlier_confirmation(self):
        spec = valid_spec()
        flow_id = only_flow(spec)["id"]
        payload = session(spec, [
            record(1, flow_id, "app-home", "navigation"),
            record(2, flow_id, "app-home", "navigation", "change-requested", "Start elsewhere"),
            record(3, flow_id, "record-list", "navigation"),
        ])
        plan = review_apply.build_plan(payload, spec, Path("prototype"))
        self.assertEqual(plan["safeConfirmations"], [])
        latest = next(item for item in plan["items"] if item["key"]["stateId"] == "app-home")
        self.assertEqual(latest["latestDecision"], "change-requested")
        self.assertEqual(latest["historyCount"], 2)

    def test_free_text_and_drafts_are_agent_work_not_graph_mutations(self):
        spec = valid_spec()
        flow_id = only_flow(spec)["id"]
        payload = session(
            spec,
            [record(1, flow_id, "decision", "branches", "question", "Add a third branch?")],
            drafts=[{"flowId": flow_id, "stateId": "decision", "note": "unfinished"}],
        )
        plan = review_apply.build_plan(payload, spec, Path("prototype"))
        self.assertIn("review session contains unfinished drafts", plan["blockers"])
        self.assertEqual(plan["summary"]["needsAgent"], 1)
        self.assertEqual(plan["safeConfirmations"], [])

    def test_stale_snapshot_blocks_apply(self):
        spec = valid_spec()
        payload = session(spec, [])
        changed = copy.deepcopy(spec)
        only_flow(changed)["task"] = "Changed after review"
        plan = review_apply.build_plan(payload, changed, Path("prototype"))
        self.assertFalse(plan["prototype"]["snapshotMatches"])
        self.assertTrue(any("specSnapshot" in blocker for blocker in plan["blockers"]))

    def test_mismatched_record_snapshot_is_stale_and_blocks_apply(self):
        spec = valid_spec()
        flow_id = only_flow(spec)["id"]
        payload = session(spec, [record(1, flow_id, "app-home", "navigation")])
        payload["records"][0]["review"][0]["proposal"] = "A different proposal"
        plan = review_apply.build_plan(payload, spec, Path("prototype"))
        self.assertEqual(plan["items"][0]["disposition"], "stale")
        self.assertEqual(plan["safeConfirmations"], [])
        self.assertTrue(any("stale" in blocker for blocker in plan["blockers"]))

    def test_malformed_draft_blocks_apply(self):
        spec = valid_spec()
        payload = session(spec, [], drafts=[None])
        plan = review_apply.build_plan(payload, spec, Path("prototype"))
        self.assertTrue(any("drafts[0]" in blocker for blocker in plan["blockers"]))

    def test_validator_conflict_keeps_entry_confirmation_manual(self):
        spec = valid_spec()
        flow_id = only_flow(spec)["id"]
        payload = session(spec, [record(1, flow_id, "app-home", "entry-point")])
        plan = review_apply.build_plan(payload, spec, Path("prototype"))
        self.assertEqual(plan["safeConfirmations"], [])
        item = next(item for item in plan["items"] if item["key"]["aspect"] == "entry-point")
        self.assertEqual(item["disposition"], "needs-agent")
        self.assertTrue(any("entry.basis" in reason for reason in item["reasons"]))


class ApplyRules(unittest.TestCase):
    def test_safe_apply_updates_flow_and_embedded_spec_together(self):
        spec = valid_spec()
        flow_id = only_flow(spec)["id"]
        payload = session(spec, [
            record(1, flow_id, "app-home", "navigation"),
            record(2, flow_id, "record-list", "navigation"),
        ])
        with tempfile.TemporaryDirectory() as temp:
            prototype_dir = Path(temp)
            flow_path = prototype_dir / "flow.json"
            prototype_path = prototype_dir / "prototype.html"
            flow_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            prototype_path.write_text(template_html(), encoding="utf-8")
            plan = review_apply.build_plan(payload, spec, prototype_dir)
            applied = review_apply.apply_confirmations(plan, payload, spec, prototype_path)
            self.assertEqual([item["aspect"] for item in applied], ["navigation"])
            updated = json.loads(flow_path.read_text(encoding="utf-8"))
            point = review(updated, "navigation")
            self.assertEqual(point["status"], "confirmed")
            self.assertIn("Client PM", point["basis"])
            embedded = re.search(
                r'<script id="flow-spec" type="application/json">(.*?)</script>',
                prototype_path.read_text(encoding="utf-8"),
                re.DOTALL,
            )
            self.assertEqual(json.loads(embedded.group(1)), updated)

    def test_apply_refuses_a_draft_even_when_confirmations_are_safe(self):
        spec = valid_spec()
        flow_id = only_flow(spec)["id"]
        payload = session(
            spec,
            [
                record(1, flow_id, "app-home", "navigation"),
                record(2, flow_id, "record-list", "navigation"),
            ],
            drafts=[{"flowId": flow_id, "stateId": "decision", "note": "unfinished"}],
        )
        plan = review_apply.build_plan(payload, spec, Path("prototype"))
        with self.assertRaises(review_apply.ReviewError):
            review_apply.apply_confirmations(plan, payload, spec, Path("prototype.html"))

    def test_apply_refuses_a_flow_changed_after_planning(self):
        spec = valid_spec()
        flow_id = only_flow(spec)["id"]
        payload = session(spec, [
            record(1, flow_id, "app-home", "navigation"),
            record(2, flow_id, "record-list", "navigation"),
        ])
        with tempfile.TemporaryDirectory() as temp:
            prototype_dir = Path(temp)
            flow_path = prototype_dir / "flow.json"
            prototype_path = prototype_dir / "prototype.html"
            flow_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            prototype_path.write_text(template_html(), encoding="utf-8")
            plan = review_apply.build_plan(payload, spec, prototype_dir)
            changed = copy.deepcopy(spec)
            only_flow(changed)["task"] = "Changed concurrently"
            flow_path.write_text(json.dumps(changed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(review_apply.ReviewError, "changed after planning"):
                review_apply.apply_confirmations(plan, payload, spec, prototype_path)


if __name__ == "__main__":
    unittest.main()
