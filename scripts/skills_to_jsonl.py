#!/usr/bin/env python3
"""Convert .claude/skills/ SKILL.md files to a JSONL file.

Each output line is a JSON object:
  {"name": "...", "description": "...", "content": "..."}
"""

import json
import re
import sys
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FIELD_RE = re.compile(r"^(\w+):\s*(.+)$", re.MULTILINE)


def parse_skill(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        print(f"  [skip] no frontmatter: {path}", file=sys.stderr)
        return None

    frontmatter = m.group(1)
    content = text[m.end():].strip()

    fields = dict(FIELD_RE.findall(frontmatter))
    name = fields.get("name", "").strip()
    # description may span multiple lines; grab everything after "description: "
    desc_match = re.search(r"^description:\s*(.+?)(?=\n\w+:|$)", frontmatter, re.DOTALL | re.MULTILINE)
    description = desc_match.group(1).strip() if desc_match else ""

    return {"name": name, "description": description, "content": content}


def main() -> None:
    skills_dir = Path(__file__).parent.parent / ".claude" / "skills"
    if not skills_dir.is_dir():
        sys.exit(f"Skills directory not found: {skills_dir}")

    output_path = Path(__file__).parent.parent / "skills.jsonl"

    skill_dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir())
    written = 0

    with output_path.open("w", encoding="utf-8") as out:
        for skill_dir in skill_dirs:
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                print(f"  [skip] missing SKILL.md: {skill_dir.name}", file=sys.stderr)
                continue
            record = parse_skill(skill_file)
            if record:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1

    print(f"Wrote {written} records to {output_path}")


if __name__ == "__main__":
    main()
