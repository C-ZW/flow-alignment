"""End-to-end checks over any artifacts committed to this repository.

PROJECT_GOALS.md requires that every generated artifact carries a walkthrough and
passes its structural validator. These tests enforce that on the real files. The
repository ships skills, not demo content, so these pass vacuously when no
artifact is present — the rules themselves are covered by the fixture-driven
tests in test_flow_spec.py and test_prototype_html.py.
"""

import json
import unittest
from pathlib import Path

from _support import ROOT, SKILLS, TEMPLATE, adaptation, flow_spec, reference

PROTOTYPES = ROOT / "prototypes"
REFERENCES = ROOT / "references"
ENGINE_MARKER = "ENGINE — generic and data driven"


def engine_block(html: str) -> str:
    return html[html.index(ENGINE_MARKER):]


def directories(parent: Path) -> list[Path]:
    if not parent.is_dir():
        return []
    return sorted(child for child in parent.iterdir() if child.is_dir())


class PrototypeArtifacts(unittest.TestCase):
    def test_every_prototype_directory_is_a_complete_artifact(self):
        for directory in directories(PROTOTYPES):
            with self.subTest(prototype=directory.name):
                missing = [
                    name
                    for name in ("flow.json", "prototype.html", "walkthrough.md")
                    if not (directory / name).is_file()
                ]
                self.assertEqual(
                    missing,
                    [],
                    f"prototypes/{directory.name} is missing {missing}. Migrate it to the current "
                    "flow.json contract or remove it.",
                )

    def test_every_prototype_passes_its_validator(self):
        for directory in directories(PROTOTYPES):
            if not (directory / "flow.json").is_file():
                continue
            with self.subTest(prototype=directory.name):
                status, issues = flow_spec.run(directory / "flow.json", directory / "prototype.html")
                reported = [f"{issue.level}: {issue.message}" for issue in issues]
                self.assertEqual(status, 0, f"prototypes/{directory.name}\n" + "\n".join(reported))

    def test_every_prototype_uses_the_unmodified_engine(self):
        expected = engine_block(TEMPLATE.read_text(encoding="utf-8"))
        for directory in directories(PROTOTYPES):
            html_path = directory / "prototype.html"
            if not html_path.is_file():
                continue
            with self.subTest(prototype=directory.name):
                html = html_path.read_text(encoding="utf-8")
                self.assertTrue(
                    ENGINE_MARKER in html,
                    f"prototypes/{directory.name} was not built from the shipped template.",
                )
                self.assertTrue(
                    engine_block(html) == expected,
                    f"prototypes/{directory.name} edited the generic engine. Flow logic belongs in flow.json.",
                )

    def test_website_derived_prototypes_declare_their_adaptation(self):
        for directory in directories(PROTOTYPES):
            path = directory / "adaptation.json"
            if not path.is_file():
                continue
            with self.subTest(prototype=directory.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                reference_path = ROOT / payload["reference"]["path"]
                self.assertTrue(reference_path.is_file(), f"Missing reference: {reference_path}")
                errors = adaptation.validate(
                    payload,
                    json.loads(reference_path.read_text(encoding="utf-8")),
                    json.loads((directory / "flow.json").read_text(encoding="utf-8")),
                )
                self.assertEqual(errors, [])


class ReferenceArtifacts(unittest.TestCase):
    def test_every_reference_directory_is_a_complete_artifact(self):
        for directory in directories(REFERENCES):
            with self.subTest(site=directory.name):
                missing = [
                    name
                    for name in ("reference.json", "ia.md", "journeys.md", "evidence.md")
                    if not (directory / name).is_file()
                ]
                self.assertEqual(missing, [], f"references/{directory.name} is missing {missing}.")

    def test_every_reference_passes_its_validator(self):
        for directory in directories(REFERENCES):
            path = directory / "reference.json"
            if not path.is_file():
                continue
            with self.subTest(site=directory.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(reference.validate(data, directory), [])


class OutputLocation(unittest.TestCase):
    def test_no_generated_artifacts_live_under_the_skills_directory(self):
        for name in ("flow.json", "test-plan.md", "adaptation.json", "reference.json"):
            with self.subTest(artifact=name):
                strays = sorted(str(path.relative_to(ROOT)) for path in SKILLS.rglob(name))
                self.assertEqual(strays, [], "Generated artifacts must not live under .claude/skills/.")

    def test_shipped_template_validates_against_its_own_embedded_spec(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        spec = json.loads(
            html.split('<script id="flow-spec" type="application/json">')[1].split("</script>")[0]
        )
        issues, models = flow_spec.validate_spec(spec)
        issues.extend(flow_spec.validate_html(spec, models, html))
        blocking = [issue.message for issue in issues if issue.level == "ERROR"]
        self.assertEqual(blocking, [])


if __name__ == "__main__":
    unittest.main()
