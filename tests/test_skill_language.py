"""OSS-facing skill sources use English prose and interface copy."""

import re
import unittest
from pathlib import Path

from _support import SKILLS


HAN_TEXT = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
PUBLIC_SKILLS = (
    SKILLS / "flow-alignment-prototype",
    SKILLS / "website-flow-reference",
)
TEXT_SUFFIXES = {".html", ".json", ".md", ".py", ".yaml", ".yml"}


class SkillLanguage(unittest.TestCase):
    def test_public_skill_sources_contain_no_chinese_copy(self):
        findings = []
        for skill in PUBLIC_SKILLS:
            for path in sorted(skill.rglob("*")):
                if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                    continue
                for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if HAN_TEXT.search(line):
                        findings.append(f"{path.relative_to(SKILLS)}:{line_number}: {line.strip()}")
        self.assertEqual(findings, [], "OSS skill copy must stay in English:\n" + "\n".join(findings))


if __name__ == "__main__":
    unittest.main()
