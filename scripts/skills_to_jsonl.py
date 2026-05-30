#!/usr/bin/env python3
"""Convert .claude/skills/ SKILL.md files to Mistral fine-tuning JSONL.

Each output line:
  {"messages": [
    {"role": "system",    "content": "<system prompt>"},
    {"role": "user",      "content": "<derived user request>"},
    {"role": "assistant", "content": "<skill content>"}
  ]}
"""

import json
import re
import sys
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

SYSTEM_PROMPT = (
    "You are an expert sales assistant. "
    "When asked about a sales topic, provide detailed, actionable guidance "
    "using frameworks, examples, and best practices."
)

# Patterns to strip from description to produce a clean user request.
# "When the user wants to improve X" → "Help me improve X"
# "When the user mentions X" phrases are stripped to keep only the action part.
_STRIP_RE = re.compile(
    r"^When the user (wants to |is trying to |needs to |asks (about |for )?)?",
    re.IGNORECASE,
)
_ALSO_RE = re.compile(r"\.\s*Also use when.*$", re.DOTALL | re.IGNORECASE)
_MENTIONS_RE = re.compile(
    r",?\s*(also )?use when the user mentions[^.]*\.", re.IGNORECASE
)


def description_to_user_message(description: str, skill_name: str) -> str:
    """Turn the frontmatter description into a natural user turn."""
    # Keep only the first sentence (up to the first period or "Also use")
    text = _ALSO_RE.sub("", description).strip()
    text = _MENTIONS_RE.sub("", text).strip().rstrip(".")

    # Strip the leading "When the user …" clause
    text = _STRIP_RE.sub("", text).strip()

    if not text:
        # Fallback: derive from skill name
        readable = skill_name.replace("-", " ")
        return f"Can you help me with {readable}?"

    # Fix third-person pronouns → first-person
    text = re.sub(r"\btheir ability\b", "my ability", text, flags=re.IGNORECASE)
    text = re.sub(r"\btheir\b", "my", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthey\b", "I", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthem\b", "me", text, flags=re.IGNORECASE)

    # Capitalise and add a question mark if it looks like an imperative/infinitive
    text = text[0].upper() + text[1:]
    if not text.endswith("?"):
        text = f"Can you help me {text[0].lower()}{text[1:]}?"

    return text


def parse_skill(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        print(f"  [skip] no frontmatter: {path}", file=sys.stderr)
        return None

    frontmatter = m.group(1)
    content = text[m.end():].strip()

    name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    desc_match = re.search(
        r"^description:\s*(.+?)(?=\n\w+:|$)", frontmatter, re.DOTALL | re.MULTILINE
    )

    name = name_match.group(1).strip() if name_match else path.parent.name
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
            skill = parse_skill(skill_file)
            if not skill:
                continue

            user_msg = description_to_user_message(skill["description"], skill["name"])

            record = {
                "messages": [
                    {"role": "system",    "content": SYSTEM_PROMPT},
                    {"role": "user",      "content": user_msg},
                    {"role": "assistant", "content": skill["content"]},
                ]
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    print(f"Wrote {written} records to {output_path}")


if __name__ == "__main__":
    main()
