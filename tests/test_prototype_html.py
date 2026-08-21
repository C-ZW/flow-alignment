"""View-layer rules for prototype.html.

The shipped template is the known-good baseline. Each test injects one defect and
asserts the validator names it, so the suite tests the rules rather than the
presence of particular markup.
"""

import json
import re
import unittest

from _support import check_html, mentions, template_html, template_spec, valid_spec


def embed(page, spec):
    """Put a mutated specification into the page so the two still agree."""
    return re.sub(
        r'(<script id="flow-spec" type="application/json">\n).*?(\n</script>)',
        lambda m: m.group(1) + json.dumps(spec, indent=2) + m.group(2),
        page,
        flags=re.S,
    )


ENTRY_ACTION = '<button class="btn-sketch-secondary" type="button" data-goto="decision">Open</button>'
BACK_ACTION = '<button class="btn-sketch-secondary" type="button" data-goto="record-list">Go back</button>'
SHELL_LINK = '<button class="shell-link" type="button" data-nav="settings">Settings</button>'
VIEWPORT = '<main id="product-viewport" aria-live="polite"></main>'
VIEWS_OPEN = '<div id="state-views" hidden>'
DONE_TEMPLATE_OPEN = '<template data-flow="sample-flow" data-state="done">'
ERROR_TEMPLATE_OPEN = '<template data-flow="sample-flow" data-state="decision" data-variant="error">'


def cut_template(html: str, open_tag: str) -> tuple[str, str]:
    """Remove one <template> block and return (remaining html, removed block)."""
    start = html.index(open_tag)
    end = html.index("</template>", start) + len("</template>")
    return html[:start] + html[end:], html[start:end]


class Baseline(unittest.TestCase):
    def test_shipped_template_is_clean(self):
        found, warned = check_html(template_html())
        self.assertEqual(found, [])
        self.assertEqual(warned, [])


class SourceOfTruth(unittest.TestCase):
    def test_embedded_spec_must_match_flow_json(self):
        spec = valid_spec()
        spec["flows"][0]["task"] = "A task the embedded copy does not have."
        found, _ = check_html(template_html(), spec)
        self.assertTrue(mentions(found, "Embedded #flow-spec differs from flow.json"))

    def test_missing_embedded_spec_is_rejected(self):
        html = template_html()
        start = html.index('<script id="flow-spec"')
        end = html.index("</script>", start) + len("</script>")
        found, _ = check_html(html[:start] + html[end:])
        self.assertTrue(mentions(found, "must embed"))

    def test_required_engine_hooks_must_exist(self):
        html = template_html().replace('id="reset-flow"', 'id="restart-button"')
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "missing the required element #reset-flow"))


class ViewportSeparation(unittest.TestCase):
    def test_product_viewport_must_be_empty_in_source(self):
        html = template_html().replace(
            VIEWPORT,
            '<main id="product-viewport" aria-live="polite"><h1>Hard-coded screen</h1></main>',
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "#product-viewport must be empty in source"))

    def test_observer_copy_may_not_appear_in_a_state_view(self):
        for phrase in ("Reset flow", "Hypothesis: admins understand", "Simulate error", "Telemetry"):
            with self.subTest(phrase=phrase):
                html = template_html().replace(ENTRY_ACTION, f"<p>{phrase}</p>" + ENTRY_ACTION)
                found, _ = check_html(html)
                self.assertTrue(mentions(found, "observer-only copy"))

    def test_observer_copy_is_caught_in_chinese_too(self):
        # An artifact written for Chinese-speaking participants leaks the same way.
        for phrase in ("重置流程", "模擬錯誤", "驗證假說", "測試任務", "模拟错误"):
            with self.subTest(phrase=phrase):
                html = template_html().replace(ENTRY_ACTION, f"<p>{phrase}</p>" + ENTRY_ACTION)
                found, _ = check_html(html)
                self.assertTrue(mentions(found, "observer-only copy"))

    def test_real_product_copy_is_not_a_false_positive(self):
        # Ordinary product words must survive: the check has to stay narrow.
        for phrase in ("重設密碼", "錯誤訊息", "測試版功能", "Reset password", "Error details"):
            with self.subTest(phrase=phrase):
                html = template_html().replace(ENTRY_ACTION, f"<p>{phrase}</p>" + ENTRY_ACTION)
                found, _ = check_html(html)
                self.assertEqual(found, [])

    def test_dimmed_product_shell_must_not_be_interactive(self):
        html = template_html().replace(
            SHELL_LINK,
            '<button type="button" data-goto="decision">Settings</button>',
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "dimmed product shell contains an interactive"))

    def test_observer_hud_must_not_carry_product_actions(self):
        anchor = '<button class="hud-button" id="reset-flow" type="button">Reset</button>'
        html = template_html().replace(anchor, anchor + '<button type="button" data-goto="done">Approve</button>')
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "observer HUD contains a product action"))

    def test_state_views_must_live_in_the_container(self):
        html, removed = cut_template(template_html(), DONE_TEMPLATE_OPEN)
        html = html.replace(VIEWS_OPEN, removed + "\n" + VIEWS_OPEN)
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "must live inside the #state-views container"))


class ShellNavigation(unittest.TestCase):
    def test_nav_key_must_exist_in_the_shell(self):
        spec = valid_spec()
        spec["flows"][0]["states"][0]["navTargets"] = {"billing": "record-list"}
        found, _ = check_html(embed(template_html(), spec), spec)
        self.assertTrue(mentions(found, "routes nav 'billing'", 'no shell element declares'))

    def test_duplicate_nav_keys_are_rejected(self):
        html = template_html().replace('data-nav="records">Records', 'data-nav="settings">Records')
        found, _ = check_html(html)
        self.assertTrue(mentions(found, 'Duplicate data-nav="settings"'))

    def test_nav_may_not_live_in_a_state_view(self):
        html = template_html().replace(ENTRY_ACTION, '<button data-nav="settings">Go</button>' + ENTRY_ACTION)
        found, _ = check_html(html)
        self.assertTrue(mentions(found, 'data-nav="settings"', "belongs to the shell"))

    def test_nav_may_not_live_in_the_rail(self):
        anchor = '<button class="hud-button" id="reset-flow" type="button">Reset</button>'
        html = template_html().replace(anchor, anchor + '<button data-nav="settings">Go</button>')
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "sits in the observer HUD"))

    def test_a_transition_offered_only_by_navigation_is_accepted(self):
        found, _ = check_html(template_html())
        self.assertEqual([e for e in found if "nothing offers" in e], [])


class ActionsMatchTheGraph(unittest.TestCase):
    def test_action_must_be_a_declared_transition_from_that_state(self):
        html = template_html().replace(ENTRY_ACTION, ENTRY_ACTION.replace('data-goto="decision"', 'data-goto="done"'))
        found, _ = check_html(html)
        self.assertTrue(mentions(found, 'data-goto="done"', "not a declared transition from 'record-list'"))

    def test_every_declared_transition_needs_an_affordance(self):
        html = template_html().replace(BACK_ACTION, "")
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "decision -> record-list", "nothing offers that action"))

    def test_every_state_needs_a_base_view(self):
        html, _ = cut_template(template_html(), DONE_TEMPLATE_OPEN)
        found, _ = check_html(html)
        self.assertTrue(mentions(found, 'data-state="done"', "No base <template"))

    def test_duplicate_view_for_one_state_is_rejected(self):
        html, removed = cut_template(template_html(), DONE_TEMPLATE_OPEN)
        html = html.replace(VIEWS_OPEN, VIEWS_OPEN + "\n" + removed + "\n" + removed)
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "Duplicate template"))

    def test_view_for_an_undeclared_state_is_rejected(self):
        html = template_html().replace(DONE_TEMPLATE_OPEN, '<template data-flow="sample-flow" data-state="ghost">')
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "undeclared state 'ghost'"))

    def test_view_for_an_undeclared_flow_is_rejected(self):
        html = template_html().replace(DONE_TEMPLATE_OPEN, '<template data-flow="other-flow" data-state="done">')
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "undeclared flow 'other-flow'"))

    def test_actions_must_be_buttons(self):
        html = template_html().replace(
            ENTRY_ACTION,
            '<a class="btn-sketch-secondary" href="#" data-goto="decision">Open</a>',
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "puts data-goto on <a>"))

    def test_observer_jump_controls_may_not_appear_in_a_state_view(self):
        # Jumping between states is a facilitator control; the HUD stepper owns it.
        html = template_html().replace(
            ENTRY_ACTION,
            '<button type="button" data-jump="done">Skip ahead</button>' + ENTRY_ACTION,
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, 'data-jump="done"', "observer control"))

    def test_inline_handlers_are_rejected(self):
        html = template_html().replace(
            ENTRY_ACTION,
            ENTRY_ACTION.replace("type=\"button\"", "type=\"button\" onclick=\"FlowPrototype.goTo('decision')\""),
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "inline handler"))


class ErrorBranch(unittest.TestCase):
    def test_error_view_requires_error_simulation(self):
        spec = valid_spec()
        spec["flows"][0]["errorSimulation"] = {"supported": False, "label": ""}
        found, _ = check_html(template_html(), spec)
        self.assertTrue(mentions(found, "declares an error variant but flow"))

    def test_error_simulation_requires_an_error_view(self):
        html, _ = cut_template(template_html(), ERROR_TEMPLATE_OPEN)
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "enables error simulation but declares no"))

    def test_unsupported_variant_is_rejected(self):
        html = template_html().replace(ERROR_TEMPLATE_OPEN, ERROR_TEMPLATE_OPEN.replace('"error"', '"loading"'))
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "unsupported data-variant"))


class OfflineGuarantees(unittest.TestCase):
    def test_blocking_dialogs_are_rejected(self):
        for call in ("alert('done')", "confirm('sure?')", "prompt('name')"):
            with self.subTest(call=call):
                html = template_html().replace("</body>", f"<script>{call}</script></body>")
                found, _ = check_html(html)
                self.assertTrue(mentions(found, "alert(), confirm(), or prompt()"))

    def test_network_calls_are_rejected(self):
        html = template_html().replace("</body>", "<script>fetch('/api/members')</script></body>")
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "must run offline"))

    def test_external_resources_only_warn(self):
        html = template_html().replace(VIEWPORT, '<img src="https://cdn.example.com/logo.png">' + VIEWPORT)
        found, warned = check_html(html)
        self.assertEqual(found, [])
        self.assertTrue(mentions(warned, "cdn.example.com"))

    def test_missing_sketchbook_language_only_warns(self):
        html = template_html().replace("Patrick Hand", "Helvetica")
        found, warned = check_html(html)
        self.assertEqual(found, [])
        self.assertTrue(mentions(warned, "Patrick Hand"))


if __name__ == "__main__":
    unittest.main()
