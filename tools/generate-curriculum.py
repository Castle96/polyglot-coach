#!/usr/bin/env python3
"""
Polyglot Coach — Curriculum Generator.

Generates YAML curriculum data for any language/level, either by prompting
an LLM or by scaffolding empty templates for manual editing.

Usage:
    # Scaffold empty structure (edit YAML files by hand)
    python tools/generate-curriculum.py scaffold fr A1 French

    # Generate with LLM (set POLYGLOT_LLM_MODEL_PATH first)
    python tools/generate-curriculum.py generate fr A1 French

    # Import from LibreLingo course directory
    python tools/generate-curriculum.py import-librelingo ./librelingo-course fr

    # Generate all CEFR levels at once
    python tools/generate-curriculum.py scaffold fr A1 French --levels A1,A2,B1
"""

import argparse
import os
import sys
import textwrap
from pathlib import Path

# --- project root ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRICULUM_DIR = PROJECT_ROOT / "curriculum"

# --- scaffold templates ---
def _manifest_content(lang_code: str, lang_name: str, levels_str: str) -> str:
    levels = [lev.strip() for lev in levels_str.split(",") if lev.strip()]
    lines = [f"language: {lang_code}", f"name: {lang_name}", "levels:"]
    lines.extend(f"  - {lev}" for lev in levels)
    lines.extend(["locales:", "  - neutral", ""])
    return "\n".join(lines)

GRAMMAR_TEMPLATE = """\
rules:
  - rule_id: {lang_code}_{level}_example_rule
    title: Example Grammar Rule
    explanation: Explain the rule here. Keep it clear and concise.
    examples: |
      Example sentence 1 (translation)
      Example sentence 2 (translation)
    level: {level}
    category: verbs
"""

SCENARIOS_TEMPLATE = """\
scenarios:
  - title: "{level_title}: Example scenario"
    context: "Describe the scenario here. What is happening? Where are they?"
    level: {level}
    roles: "Role1, Role2"
    vocabulary_hints: "word1, word2, phrase1"
    grammar_focus: "grammar-rule-id-1, grammar-rule-id-2"
"""

VOCABULARY_TEMPLATE = """\
words:
  - word: ejemplo
    translation: example
    tags: basic
"""

LOCALE_TEMPLATE = """\
locale_overrides: []

pronunciation_profiles:
  - locale: neutral
    name: Standard {lang_name}
    features:
      - "neutral pronunciation"
"""


# --- LLM prompts ---
def _llm_prompt(prompt: str, temperature: float = 0.3) -> str:
    """Call the local LLM via Ollama or llama-cpp-python to generate content."""

    # Try Ollama first
    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    ollama_model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    try:
        import urllib.request
        import json
        resp = urllib.request.urlopen(f"{ollama_host}/api/tags", timeout=3)
        # Ollama is running — use it
        body = json.dumps({
            "model": ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": 4096},
        }).encode()
        req = urllib.request.Request(
            f"{ollama_host}/api/generate", data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=300)
        data = json.loads(resp.read())
        return data.get("response", "").strip()
    except Exception:
        pass

    # Fallback: llama-cpp-python with a local GGUF
    try:
        from llama_cpp import Llama
    except ImportError:
        print("ERROR: No LLM available. Install Ollama or llama-cpp-python.")
        sys.exit(1)

    model_path = os.environ.get("POLYGLOT_LLM_MODEL_PATH")
    if not model_path:
        print("ERROR: Set POLYGLOT_LLM_MODEL_PATH to a GGUF file, or install Ollama.")
        print("  Example: export POLYGLOT_LLM_MODEL_PATH=~/models/qwen2.5-7b-q4.gguf")
        sys.exit(1)
    if not Path(model_path).exists():
        print(f"ERROR: Model not found: {model_path}")
        sys.exit(1)

    print(f"  Loading LLM ({model_path})...")
    llm = Llama(model_path=model_path, n_ctx=4096, verbose=False)
    response = llm(
        prompt,
        max_tokens=4096,
        temperature=temperature,
        stop=["<|user|>", "<|system|>", "```"],
    )
    text = response["choices"][0]["text"].strip() if response.get("choices") else ""
    return text


def _generate_grammar(lang_code: str, lang_name: str, level: str) -> str:
    prompt = f"""Generate exactly 15 grammar rules for {lang_name} ({lang_code}) at CEFR level {level}.
Return ONLY valid YAML (no markdown, no backticks) using this structure:

rules:
  - rule_id: {lang_code}_{level}_unique_id
    title: Short Title
    explanation: "Concise explanation of the rule with examples in context."
    examples: |
      Example sentence 1 (translation)
      Example sentence 2 (translation)
    level: {level}
    category: one_of: verbs/nouns/pronouns/syntax/prepositions/adjectives

Cover the most important grammar points for this level."""
    print(f"  Generating {level} grammar rules...")
    return _llm_prompt(prompt)


def _generate_vocabulary(lang_code: str, lang_name: str, level: str) -> str:
    prompt = f"""Generate exactly 80 vocabulary words for {lang_name} ({lang_code}) at CEFR level {level}.
Return ONLY valid YAML (no markdown, no backticks) using this structure:

words:
  - word: word_in_{lang_code}
    translation: english_translation
    tags: comma,separated,tags

Include words from these categories: greetings, numbers, colors, family, food, daily routine, travel, questions.
Cover the most essential vocabulary for this level."""
    print(f"  Generating {level} vocabulary...")
    return _llm_prompt(prompt)


def _generate_scenarios(lang_code: str, lang_name: str, level: str) -> str:
    prompt = f"""Generate exactly 8 conversation scenarios for {lang_name} ({lang_code}) at CEFR level {level}.
Return ONLY valid YAML (no markdown, no backticks) using this structure:

scenarios:
  - title: "Theme: Specific Situation"
    context: "Describe the situation in detail. Who, what, where, why."
    level: {level}
    roles: "Participant1, Participant2"
    vocabulary_hints: "key_word_1, key_phrase_1, key_word_2"
    grammar_focus: "rule_id_1, rule_id_2"

Make scenarios practical for real-life situations appropriate to this level."""
    print(f"  Generating {level} scenarios...")
    return _llm_prompt(prompt)


# --- commands ---

def cmd_scaffold(args):
    """Create empty YAML structure for a language/level."""
    lang_dir = CURRICULUM_DIR / args.lang_code
    level_dir = lang_dir / args.level

    if level_dir.exists():
        print(f"EXISTS: {level_dir}")
        if not args.force:
            print("  Use --force to overwrite")
            return

    level_dir.mkdir(parents=True, exist_ok=True)

    # manifest
    manifest_path = lang_dir / "manifest.yaml"
    if not manifest_path.exists() or args.force:
        levels_str = args.levels if args.levels else args.level
        manifest_path.write_text(_manifest_content(args.lang_code, args.lang_name, levels_str))
        print(f"  Created: {manifest_path}")

    # level files
    for filename, template in [
        ("grammar.yaml", GRAMMAR_TEMPLATE),
        ("scenarios.yaml", SCENARIOS_TEMPLATE),
        ("vocabulary.yaml", VOCABULARY_TEMPLATE),
        ("locale.yaml", LOCALE_TEMPLATE),
    ]:
        path = level_dir / filename
        if not path.exists() or args.force:
            content = template.format(lang_code=args.lang_code, lang_name=args.lang_name, level=args.level, level_title=f"{args.lang_name} {args.level}")
            path.write_text(content)
            print(f"  Created: {path}")

    print(f"\nDone! Edit the YAML files in: {level_dir}")


def cmd_generate(args):
    """Use LLM to generate curriculum content for a language/level."""
    lang_dir = CURRICULUM_DIR / args.lang_code
    level_dir = lang_dir / args.level
    level_dir.mkdir(parents=True, exist_ok=True)

    # manifest
    manifest_path = lang_dir / "manifest.yaml"
    if not manifest_path.exists() or args.force:
        levels_str = args.levels if args.levels else args.level
        manifest_path.write_text(_manifest_content(args.lang_code, args.lang_name, levels_str))
        print(f"  Created: {manifest_path}")

    # grammar
    grammar = _generate_grammar(args.lang_code, args.lang_name, args.level)
    (level_dir / "grammar.yaml").write_text(grammar)
    print(f"  Wrote: {level_dir / 'grammar.yaml'}")

    # vocabulary
    vocab = _generate_vocabulary(args.lang_code, args.lang_name, args.level)
    (level_dir / "vocabulary.yaml").write_text(vocab)
    print(f"  Wrote: {level_dir / 'vocabulary.yaml'}")

    # scenarios
    scenarios = _generate_scenarios(args.lang_code, args.lang_name, args.level)
    (level_dir / "scenarios.yaml").write_text(scenarios)
    print(f"  Wrote: {level_dir / 'scenarios.yaml'}")

    # locale — empty template
    locale_path = level_dir / "locale.yaml"
    if not locale_path.exists() or args.force:
        locale_path.write_text(LOCALE_TEMPLATE.format(lang_name=args.lang_name))
        print(f"  Wrote: {locale_path}")

    print(f"\nDone! Generated {args.level} content for {args.lang_name} in {level_dir}")


def cmd_import_librelingo(args):
    """Import a LibreLingo course directory into curriculum YAML format.

    LibreLingo courses are structured as:
        course/
          index.yaml
          modules/
            module_name/
              index.yaml
              skills/
                skill_name/
                  index.yaml
                  phrases.yaml

    This converts the skill data into our scenario/vocabulary/grammar format.
    """
    course_dir = Path(args.course_dir)
    if not course_dir.exists():
        print(f"ERROR: Course directory not found: {course_dir}")
        sys.exit(1)

    lang_code = args.lang_code
    lang_dir = CURRICULUM_DIR / lang_code
    lang_dir.mkdir(parents=True, exist_ok=True)

    # Read course index
    try:
        import yaml
    except ImportError:
        print("Install pyyaml: uv pip install pyyaml")
        sys.exit(1)

    course_index = course_dir / "index.yaml"
    if course_index.exists():
        with open(course_index) as f:
            meta = yaml.safe_load(f) or {}
        lang_name = meta.get("language_name", lang_code)
    else:
        lang_name = lang_code

    # manifest
    manifest_path = lang_dir / "manifest.yaml"
    if not manifest_path.exists():
        manifest_path.write_text(_manifest_content(lang_code, lang_name, "A1"))
        print(f"  Created: {manifest_path}")

    # Walk modules/skills
    modules_dir = course_dir / "modules"
    if not modules_dir.exists():
        print(f"ERROR: No modules/ directory in {course_dir}")
        sys.exit(1)

    all_words = []
    all_scenarios = []
    seen_words = set()

    for mod_dir in sorted(modules_dir.iterdir()):
        if not mod_dir.is_dir():
            continue
        skills_dir = mod_dir / "skills"
        if not skills_dir.exists():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            phrases_path = skill_dir / "phrases.yaml"
            if not phrases_path.exists():
                continue
            with open(phrases_path) as f:
                phrases = yaml.safe_load(f) or {}

            skill_name = skill_dir.name.replace("_", " ").title()

            scenario_phrases = []
            for item in phrases if isinstance(phrases, list) else phrases.get("phrases", []):
                if isinstance(item, dict):
                    word = item.get("word") or item.get("from", "")
                    translation = item.get("translation") or item.get("to", "")
                    if word and translation and word not in seen_words:
                        seen_words.add(word)
                        all_words.append({
                            "word": word,
                            "translation": translation,
                            "tags": _detect_tags(skill_name),
                        })
                    if word:
                        scenario_phrases.append(word)

            if scenario_phrases:
                all_scenarios.append({
                    "title": f"{skill_name}",
                    "context": f"Practice {skill_name.lower()} in {lang_name}.",
                    "level": "A1",
                    "roles": "Learner, Tutor",
                    "vocabulary_hints": ", ".join(scenario_phrases[:10]),
                    "grammar_focus": "",
                })

    # Write vocabulary
    if all_words:
        vocab_path = lang_dir / "A1" / "vocabulary.yaml"
        (lang_dir / "A1").mkdir(parents=True, exist_ok=True)
        vocab_path.write_text("words:\n" + "\n".join(
            f"  - word: {w['word']}\n    translation: {w['translation']}\n    tags: {w['tags']}"
            for w in all_words
        ))
        print(f"  Wrote {len(all_words)} words to: {vocab_path}")

    # Write scenarios
    if all_scenarios:
        sc_path = lang_dir / "A1" / "scenarios.yaml"
        sc_content = "scenarios:\n"
        for sc in all_scenarios:
            sc_content += textwrap.dedent(f"""\
              - title: "{sc['title']}"
                context: "{sc['context']}"
                level: {sc['level']}
                roles: "{sc['roles']}"
                vocabulary_hints: "{sc['vocabulary_hints']}"
                grammar_focus: "{sc['grammar_focus']}"
            """)
        sc_path.write_text(sc_content)
        print(f"  Wrote {len(all_scenarios)} scenarios to: {sc_path}")

    if not all_words and not all_scenarios:
        print("  No phrases found. Check the LibreLingo course structure.")
    else:
        print(f"\nDone! Imported {len(all_words)} words and {len(all_scenarios)} scenarios.")


def _detect_level(skill_name: str) -> str:
    skill_lower = skill_name.lower()
    if any(w in skill_lower for w in ["intro", "basic", "hello", "alphabet"]):
        return "A1"
    if any(w in skill_lower for w in ["family", "food", "travel", "numbers"]):
        return "A1"
    return "A2"


def _detect_tags(skill_name: str) -> str:
    skill_lower = skill_name.lower()
    tag_map = {
        "greeting": ["hello", "hi", "goodbye", "greet", "introduc"],
        "food": ["food", "restaurant", "eat", "drink", "meal"],
        "travel": ["travel", "hotel", "directions", "transport"],
        "family": ["family", "mother", "father", "brother"],
        "daily": ["routine", "daily", "time", "schedule"],
        "shopping": ["shop", "buy", "store", "price", "clothes"],
    }
    tags = []
    for tag, keywords in tag_map.items():
        if any(kw in skill_lower for kw in keywords):
            tags.append(tag)
    return ",".join(tags) if tags else "vocabulary"


# --- main ---

def main():
    parser = argparse.ArgumentParser(description="Polyglot Coach Curriculum Generator")
    sub = parser.add_subparsers(dest="command", required=True)

    # scaffold
    p = sub.add_parser("scaffold", help="Create empty YAML structure for manual editing")
    p.add_argument("lang_code", help="Language code (es, fr, de, ja)")
    p.add_argument("level", help="CEFR level (A1, A2, B1)")
    p.add_argument("lang_name", help="Language name (Spanish, French, German)")
    p.add_argument("--force", "-f", action="store_true", help="Overwrite existing files")
    p.add_argument("--levels", help="Comma-separated levels for manifest (default: same as level)")

    # generate
    p = sub.add_parser("generate", help="Generate curriculum content using LLM")
    p.add_argument("lang_code", help="Language code")
    p.add_argument("level", help="CEFR level")
    p.add_argument("lang_name", help="Language name")
    p.add_argument("--force", "-f", action="store_true", help="Regenerate existing files")
    p.add_argument("--levels", help="Comma-separated levels for manifest")
    p.add_argument("--model", help="Override POLYGLOT_LLM_MODEL_PATH")

    # import-librelingo
    p = sub.add_parser("import-librelingo", help="Import from LibreLingo course directory")
    p.add_argument("course_dir", help="Path to LibreLingo course directory")
    p.add_argument("lang_code", help="Language code for the curriculum directory")
    p.add_argument("--force", "-f", action="store_true", help="Overwrite existing files")

    args = parser.parse_args()

    if args.command == "scaffold":
        cmd_scaffold(args)
    elif args.command == "generate":
        if args.model:
            os.environ["POLYGLOT_LLM_MODEL_PATH"] = args.model
        cmd_generate(args)
    elif args.command == "import-librelingo":
        cmd_import_librelingo(args)


if __name__ == "__main__":
    main()
