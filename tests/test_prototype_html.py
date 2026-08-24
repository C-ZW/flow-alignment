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
RETRY_ACTION = '<button class="btn-sketch-primary" type="button" data-goto="decision">Try again</button>'
SHELL_LINK = '<button class="shell-link" type="button" data-nav="settings">Settings</button>'
VIEWPORT = '<main id="product-viewport" aria-live="polite"></main>'
VIEWS_OPEN = '<div id="state-views" hidden>'
DONE_TEMPLATE_OPEN = '<template data-flow="sample-flow" data-state="done">'


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


class RuntimeHardening(unittest.TestCase):
    def test_only_declared_product_controls_can_use_pointer_or_keyboard_input(self):
        page = template_html()
        self.assertIn("control.style.pointerEvents = 'none'", page)
        self.assertIn("this.viewport.addEventListener('click'", page)
        self.assertIn("this.shell.addEventListener('keydown'", page)
        self.assertIn("event.preventDefault();", page)
        self.assertIn("event.stopPropagation();", page)
        self.assertIn("this.liveProductActions.includes(trigger)", page)
        self.assertIn("this.liveNavigation.includes(link)", page)
        self.assertIn("[role=\"button\"]", page)
        self.assertIn("[role=\"link\"]", page)
        self.assertIn("}, true);", page)

    def test_a_data_goto_spotlight_root_is_an_enabled_action(self):
        page = template_html()
        self.assertIn("target.matches('[data-goto]') ? [target] : []", page)
        self.assertIn("Array.from(target.querySelectorAll('[data-goto]'))", page)
        self.assertIn("this.liveProductActions = [...new Set(liveProductActions)]", page)
        self.assertIn("target.matches('[data-goto]') ? target : target.querySelector('[data-goto]')", page)

    def test_spotlight_scroll_checks_both_visible_edges_and_prefers_the_action(self):
        page = template_html()
        self.assertIn("target.top < visibleTop + inset", page)
        self.assertIn("target.bottom > visibleBottom - inset", page)
        self.assertIn("target.height > visibleHeight && actionTarget", page)
        self.assertIn("scrollTarget.scrollIntoView", page)

    def test_multi_spotlight_updates_reuse_existing_ring_nodes(self):
        page = template_html()
        self.assertIn("Array.from(this.mask.querySelectorAll('.spotlight-ring'))", page)
        self.assertIn("while (rings.length > holes.length", page)
        self.assertNotIn("const rings = [this.spotlightRing]", page)

    def test_generic_template_typography_never_drops_below_13px(self):
        css = re.search(r"<style>(.*?)</style>", template_html(), flags=re.S).group(1)
        self.assertRegex(css, r"small\s*\{[^}]*font-size:\s*13px")
        declarations = re.findall(r"(?<![\w-])font(?:-size)?\s*:\s*([^;{}]+)", css)
        sizes = [
            float(value)
            for declaration in declarations
            for value in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)px", declaration)
        ]
        self.assertTrue(sizes)
        self.assertGreaterEqual(min(sizes), 13)


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

    def test_duplicate_flow_spec_container_is_rejected(self):
        html = template_html().replace(
            '<script id="flow-spec" type="application/json">',
            '<script id="flow-spec" type="application/json"></script>\n'
            '<script id="flow-spec" type="application/json">',
            1,
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "exactly one #flow-spec", "found 2"))

    def test_flow_spec_container_must_be_a_script(self):
        html = template_html().replace(
            '<script id="flow-spec" type="application/json">',
            '<div id="flow-spec">',
            1,
        )
        html = html.replace(
            '</script>\n\n<!-- ========================================================================\n'
            '     STATE VIEWS',
            '</div>\n\n<!-- ========================================================================\n'
            '     STATE VIEWS',
            1,
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "#flow-spec must be <script>", "found <div>"))

    def test_duplicate_state_views_container_is_rejected(self):
        html = template_html().replace(
            '<div id="state-views" hidden>',
            '<div id="state-views" hidden></div>\n<div id="state-views" hidden>',
            1,
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "exactly one #state-views", "found 2"))

    def test_duplicate_product_viewport_hook_is_rejected(self):
        html = template_html().replace(
            '<main id="product-viewport" aria-live="polite"></main>',
            '<main id="product-viewport" aria-live="polite"></main>\n'
            '<main id="product-viewport" aria-live="polite"></main>',
            1,
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "exactly one #product-viewport", "found 2"))

    def test_state_views_container_must_be_a_div(self):
        html = template_html().replace(
            '<div id="state-views" hidden>',
            '<section id="state-views" hidden>',
            1,
        )
        html = html.replace(
            '\n</div>\n\n<!-- ========================================================================\n'
            '     ENGINE',
            '\n</section>\n\n<!-- ========================================================================\n'
            '     ENGINE',
            1,
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "#state-views must be <div>", "found <section>"))

    def test_required_engine_hooks_must_exist(self):
        html = template_html().replace('id="reset-flow"', 'id="restart-button"')
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "missing the required element #reset-flow"))

    def test_raw_text_between_editable_regions_is_rejected(self):
        html = template_html().replace(
            "</script>\n\n<!-- ========================================================================\n     STATE VIEWS",
            "</script>\n] }\n<!-- ========================================================================\n     STATE VIEWS",
            1,
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "raw text between its editable regions", "closing tag"))

    def test_the_rail_regions_the_engine_renders_into_must_exist(self):
        # Entry declaration, direct route map, and restart are engine contract.
        for element_id in ("entry-block", "entry-basis", "entry-why", "entry-preconditions",
                           "route-details", "reset-flow"):
            with self.subTest(element=element_id):
                html = template_html().replace(f'id="{element_id}"', 'id="renamed-by-hand"', 1)
                found, _ = check_html(html)
                self.assertTrue(mentions(found, f"missing the required element #{element_id}"))

    def test_dense_rail_sections_are_collapsed_by_default(self):
        page = template_html()
        for class_name in ("hud-scenario", "hud-entry", "hud-step-note"):
            with self.subTest(section=class_name):
                tag = re.search(rf'<details[^>]*class="[^"]*{class_name}[^"]*"[^>]*>', page)
                self.assertIsNotNone(tag)
                self.assertNotRegex(tag.group(0), r"\sopen(?:\s|=|>)")

    def test_route_map_is_open_by_default(self):
        tag = re.search(r'<details[^>]*class="[^"]*route-details[^"]*"[^>]*>', template_html())
        self.assertIsNotNone(tag)
        self.assertRegex(tag.group(0), r"\sopen(?:\s|=|>)")

    def test_restart_is_the_only_fixed_rail_button(self):
        rail = template_html().split('<aside class="observer-hud"', 1)[1].split("</aside>", 1)[0]
        button_ids = re.findall(r'<button[^>]+id="([^"]+)"', rail)
        self.assertEqual(button_ids, ["reset-flow"])

    def test_each_route_step_is_a_direct_jump_button(self):
        page = template_html()
        self.assertIn('this.stepper.addEventListener(\'click\'', page)
        self.assertIn('data-jump="${item.id}"', page)
        self.assertIn('this.jumpTo(step.dataset.jump)', page)
        self.assertNotIn('data-visited=', page)

    def test_mask_limits_keyboard_interaction_to_declared_controls(self):
        page = template_html()
        self.assertIn("control.tabIndex = -1", page)
        self.assertIn("if ('disabled' in control) control.disabled = true", page)
        self.assertIn("Array.from(target.querySelectorAll('[data-goto]'))", page)
        self.assertIn("...(state.scope === 'shell' ? liveNavigation : [])", page)

    def test_structural_viewport_cannot_be_disabled_by_runtime_focus(self):
        page = template_html()
        self.assertIn(
            ").filter((control) => control !== this.viewport);",
            page,
        )
        self.assertIn("const temporaryViewportTabIndex = target === this.viewport", page)
        self.assertIn("if (temporaryViewportTabIndex) target.removeAttribute('tabindex');", page)

    def test_mobile_rail_uses_content_height_before_it_scrolls(self):
        page = template_html()
        self.assertIn("height: auto; max-height: min(46vh, 420px)", page)
        self.assertNotIn("\n        height: min(46vh, 420px)", page)

    def test_rail_has_no_review_data_entry_controls(self):
        rail = template_html().split('<aside class="observer-hud"', 1)[1].split("</aside>", 1)[0]
        for fragment in ("<input", "<textarea", "<form", "confirm-step", "feedback-toggle", "export-feedback"):
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, rail)


class ViewportSeparation(unittest.TestCase):
    def test_product_viewport_must_be_empty_in_source(self):
        html = template_html().replace(
            VIEWPORT,
            '<main id="product-viewport" aria-live="polite"><h1>Hard-coded screen</h1></main>',
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "#product-viewport must be empty in source"))

    def test_product_css_must_not_override_mask_geometry(self):
        marker = "/* ---- Product-specific additions go below this line. ---- */"
        for rule in (
            "#product-viewport { z-index: 99; }",
            "#interaction-mask { display: none; }",
            ".spotlight-ring { opacity: 0; }",
            ".mask-pane { opacity: 0; }",
        ):
            with self.subTest(rule=rule):
                html = template_html().replace(marker, marker + "\n" + rule)
                found, _ = check_html(html)
                self.assertTrue(mentions(found, "Product CSS"))

    def test_each_state_template_needs_its_declared_spotlight(self):
        html = template_html().replace(' data-spotlight="decision-actions"', "", 1)
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "needs exactly one", 'data-spotlight="decision-actions"'))

    def test_product_actions_must_be_inside_the_declared_spotlight(self):
        html = template_html().replace(
            '<div class="actions" data-spotlight="decision-actions">',
            '<div data-spotlight="decision-actions"></div><div class="actions">',
            1,
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "outside its declared spotlight", "decision-actions"))

    def test_multi_region_state_requires_each_region_and_accepts_actions_in_either(self):
        spec = valid_spec()
        decision = next(item for item in spec["flows"][0]["states"] if item["id"] == "decision")
        del decision["spotlight"]
        decision["spotlights"] = ["decision-context", "decision-actions"]
        html = template_html().replace(
            '<p class="note">Put the trade-off, friction, or value proposition being confirmed right here, in product language.</p>',
            '<p class="note" data-spotlight="decision-context">Put the trade-off, friction, or value proposition being confirmed right here, in product language.</p>',
            1,
        )
        html = embed(html, spec)
        found, warned = check_html(html, spec)
        self.assertEqual(found, [])
        self.assertEqual(warned, [])

        missing = html.replace(' data-spotlight="decision-context"', "", 1)
        found, _ = check_html(missing, spec)
        self.assertTrue(mentions(found, "needs exactly one", 'data-spotlight="decision-context"'))

    def test_multi_region_scroll_prefers_the_region_with_the_next_action(self):
        self.assertIn(
            ".map((target) => target.matches('[data-goto]') ? target : target.querySelector('[data-goto]'))",
            template_html(),
        )
        self.assertIn(".find(Boolean)", template_html())

    def test_mobile_route_map_cannot_expand_the_rail_track(self):
        page = template_html()
        self.assertIn(".observer-hud > *, .hud-current, .route-details { min-width: 0; }", page)
        self.assertIn(".stepper { display: flex; min-width: 0; max-width: 100%; overflow-x: auto; }", page)

    def test_product_css_must_not_create_a_context_above_the_mask(self):
        marker = "/* ---- Product-specific additions go below this line. ---- */"
        html = template_html().replace(marker, marker + "\n.product-context { opacity: .8; }")
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "traps routed navigation"))

    def test_observer_copy_may_not_appear_in_a_state_view(self):
        for phrase in ("Reset flow", "Hypothesis: admins understand", "Simulate error", "Telemetry"):
            with self.subTest(phrase=phrase):
                html = template_html().replace(ENTRY_ACTION, f"<p>{phrase}</p>" + ENTRY_ACTION)
                found, _ = check_html(html)
                self.assertTrue(mentions(found, "observer-only copy"))

    def test_real_product_copy_is_not_a_false_positive(self):
        # Ordinary product words must survive: the check has to stay narrow.
        for phrase in ("Reset password", "Error details", "Preview release"):
            with self.subTest(phrase=phrase):
                html = template_html().replace(ENTRY_ACTION, f"<p>{phrase}</p>" + ENTRY_ACTION)
                found, _ = check_html(html)
                self.assertEqual(found, [])

    def test_localized_observer_copy_is_still_caught(self):
        # Escaped literals keep the OSS source English-only while preserving
        # validation for localized product artifacts.
        phrase = "\u91cd\u7f6e\u6d41\u7a0b"
        html = template_html().replace(ENTRY_ACTION, f"<p>{phrase}</p>" + ENTRY_ACTION)
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "observer-only copy"))

    def test_dimmed_product_shell_must_not_be_interactive(self):
        html = template_html().replace(
            SHELL_LINK,
            '<button type="button" data-goto="decision">Settings</button>',
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "dimmed product shell contains an interactive"))

    def test_observer_hud_must_not_carry_product_actions(self):
        anchor = '<button class="hud-button" id="reset-flow" type="button">Restart</button>'
        html = template_html().replace(anchor, anchor + '<button type="button" data-goto="done">Approve</button>')
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "observer HUD contains a product action"))

    def test_state_views_must_live_in_the_container(self):
        html, removed = cut_template(template_html(), DONE_TEMPLATE_OPEN)
        html = html.replace(VIEWS_OPEN, removed + "\n" + VIEWS_OPEN)
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "must live inside the #state-views container"))


class ShellNavigation(unittest.TestCase):
    def test_navigation_only_shell_focuses_the_live_navigation(self):
        html = template_html()
        self.assertIn("const navigationOnly = state.scope === 'shell'", html)
        self.assertIn("this.spotlightTargets = navigationOnly ? [liveNavigation[0]] : productTargets", html)
        self.assertIn('data-focus-source="product"', html)

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
        anchor = '<button class="hud-button" id="reset-flow" type="button">Restart</button>'
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

    def test_every_state_needs_a_view(self):
        html, _ = cut_template(template_html(), DONE_TEMPLATE_OPEN)
        found, _ = check_html(html)
        self.assertTrue(mentions(found, 'data-state="done"', "No <template"))

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
        # Jumping between states is an author control; the rail owns it.
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


class OfflineGuarantees(unittest.TestCase):
    def test_restrictive_content_security_policy_is_required(self):
        self.assertIn("connect-src 'none'", template_html())
        without_policy = re.sub(
            r'\n  <meta http-equiv="Content-Security-Policy"[^>]+>',
            "",
            template_html(),
            count=1,
        )
        found, _ = check_html(without_policy)
        self.assertTrue(mentions(found, "exactly one Content-Security-Policy"))

        weakened = template_html().replace("connect-src 'none'", "connect-src https://collector.example")
        found, _ = check_html(weakened)
        self.assertTrue(mentions(found, "directive connect-src", "too permissive"))

    def test_content_security_policy_must_precede_executable_or_fetchable_content(self):
        page = template_html()
        policy = re.search(
            r'<meta http-equiv="Content-Security-Policy"[^>]+>',
            page,
        ).group(0)
        late_policy = page.replace(policy, "", 1).replace("</body>", f"{policy}\n</body>")
        found, _ = check_html(late_policy)
        self.assertTrue(mentions(found, "inside <head>", "precede every"))

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

    def test_computed_network_calls_and_remote_dom_assignments_are_rejected(self):
        for call in (
            "window['fetch']('https://api.example.com/members')",
            'globalThis["fetch"]("https://api.example.com/members")',
            "const image = new Image(); image.setAttribute('src', 'https://cdn.example.com/pixel.gif')",
            "const use = document.createElement('use'); use.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', 'https://cdn.example.com/icon.svg')",
            "document.createElement('script').src = 'https://cdn.example.com/loader.js'",
            "node['src'] = 'https://cdn.example.com/image.png'",
        ):
            with self.subTest(call=call):
                html = template_html().replace("</body>", f"<script>{call}</script></body>")
                found, _ = check_html(html)
                self.assertTrue(mentions(found, "must run offline"))

    def test_svg_external_xlink_href_is_rejected(self):
        html = template_html().replace(
            ENTRY_ACTION,
            '<svg><use xlink:href="https://cdn.example.com/icon.svg"></use></svg>' + ENTRY_ACTION,
            1,
        )
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "cdn.example.com", "not permitted"))

    def test_external_resources_are_rejected(self):
        html = template_html().replace(VIEWPORT, '<img src="https://cdn.example.com/logo.png">' + VIEWPORT)
        found, _ = check_html(html)
        self.assertTrue(mentions(found, "cdn.example.com", "not permitted"))

    def test_missing_sketchbook_language_only_warns(self):
        html = template_html().replace("Patrick Hand", "Helvetica")
        found, warned = check_html(html)
        self.assertEqual(found, [])
        self.assertTrue(mentions(warned, "Patrick Hand"))


if __name__ == "__main__":
    unittest.main()
