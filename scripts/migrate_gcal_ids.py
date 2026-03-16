#!/usr/bin/env python3
"""
Migrate Google Calendar event IDs from the old verbose format to the raw source ID.

Old format: gcal-pvyboch1_gmail.com-1knhu54jnmk4j8bp8eji5eno0p
New format: 1knhu54jnmk4j8bp8eji5eno0p

Updates:
  - events.yaml          (event id field)
  - tasks.md             (inline @old-id references)
  - notes/*.md           (frontmatter event_ids + inline @old-id references)
  - projects/*.md        (frontmatter event_ids + inline @old-id references)

Usage:
  python scripts/migrate_gcal_ids.py [--data-root ~/Documents/Gera] [--dry-run]
"""

import argparse
import re
import sys
from pathlib import Path

import yaml


# ── Helpers ───────────────────────────────────────────────────────────────────

GCAL_ID_RE = re.compile(r'^gcal-[^-]+-(.+)$')


def extract_new_id(old_id: str) -> str | None:
    """Return the UUID portion of an old-style gcal ID, or None if not applicable."""
    m = GCAL_ID_RE.match(old_id)
    return m.group(1) if m else None


def build_id_map(events: list[dict]) -> dict[str, str]:
    """Return {old_id: new_id} for every gcal event that needs renaming."""
    mapping = {}
    for ev in events:
        old_id = ev.get('id', '')
        new_id = extract_new_id(old_id)
        if new_id and new_id != old_id:
            mapping[old_id] = new_id
    return mapping


def replace_ids_in_text(text: str, mapping: dict[str, str]) -> str:
    """Replace all @old-id occurrences with @new-id in markdown text."""
    for old_id, new_id in mapping.items():
        text = text.replace(f'@{old_id}', f'@{new_id}')
    return text


def replace_ids_in_frontmatter_list(ids: list, mapping: dict[str, str]) -> list:
    return [mapping.get(i, i) for i in ids]


# ── Per-file migration ────────────────────────────────────────────────────────

def migrate_events_yaml(path: Path, mapping: dict[str, str], dry_run: bool) -> int:
    data = yaml.safe_load(path.read_text())
    events = data.get('events', [])
    changed = 0
    for ev in events:
        old_id = ev.get('id', '')
        if old_id in mapping:
            ev['id'] = mapping[old_id]
            changed += 1
    if changed and not dry_run:
        path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))
    print(f"  events.yaml: {changed} event(s) renamed")
    return changed


def migrate_markdown_file(path: Path, mapping: dict[str, str], dry_run: bool) -> int:
    original = path.read_text()
    result = original
    changed = 0

    # Replace frontmatter event_ids list entries
    def replace_frontmatter(m: re.Match) -> str:
        nonlocal changed
        fm_text = m.group(1)
        fm = yaml.safe_load(fm_text) or {}
        if 'event_ids' in fm:
            new_ids = replace_ids_in_frontmatter_list(fm['event_ids'], mapping)
            if new_ids != fm['event_ids']:
                changed += len([a for a, b in zip(fm['event_ids'], new_ids) if a != b])
                fm['event_ids'] = new_ids
                new_fm = yaml.dump(fm, allow_unicode=True, sort_keys=False).rstrip('\n')
                return f'---\n{new_fm}\n---'
        return m.group(0)

    result = re.sub(r'^---\n(.*?)\n---', replace_frontmatter, result, flags=re.DOTALL | re.MULTILINE)

    # Replace inline @old-id references in body
    new_result = replace_ids_in_text(result, mapping)
    inline_changes = sum(
        result.count(f'@{old_id}') for old_id in mapping
    )
    if inline_changes:
        changed += inline_changes
        result = new_result

    if changed and not dry_run:
        path.write_text(result)

    return changed


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', default=str(Path.home() / 'Documents' / 'Gera'),
                        help='Path to the Gera data directory (default: ~/Documents/Gera)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print what would change without writing files')
    args = parser.parse_args()

    data_root = Path(args.data_root).expanduser().resolve()
    if not data_root.exists():
        print(f"Error: data root not found: {data_root}", file=sys.stderr)
        sys.exit(1)

    events_path = data_root / 'events.yaml'
    if not events_path.exists():
        print(f"Error: events.yaml not found at {events_path}", file=sys.stderr)
        sys.exit(1)

    # Build the old→new ID mapping from events.yaml
    data = yaml.safe_load(events_path.read_text())
    mapping = build_id_map(data.get('events', []))

    if not mapping:
        print("No old-style gcal IDs found. Nothing to do.")
        return

    print(f"{'DRY RUN — ' if args.dry_run else ''}Migrating {len(mapping)} event ID(s):")
    for old, new in mapping.items():
        print(f"  {old}  →  {new}")
    print()

    total = 0

    # events.yaml
    total += migrate_events_yaml(events_path, mapping, args.dry_run)

    # tasks.md
    tasks_path = data_root / 'tasks.md'
    if tasks_path.exists():
        n = migrate_markdown_file(tasks_path, mapping, args.dry_run)
        print(f"  tasks.md: {n} reference(s) updated")
        total += n

    # notes/*.md
    notes_dir = data_root / 'notes'
    if notes_dir.exists():
        for md in sorted(notes_dir.glob('*.md')):
            n = migrate_markdown_file(md, mapping, args.dry_run)
            if n:
                print(f"  notes/{md.name}: {n} reference(s) updated")
                total += n

    # projects/*.md
    projects_dir = data_root / 'projects'
    if projects_dir.exists():
        for md in sorted(projects_dir.glob('*.md')):
            n = migrate_markdown_file(md, mapping, args.dry_run)
            if n:
                print(f"  projects/{md.name}: {n} reference(s) updated")
                total += n

    print()
    if args.dry_run:
        print(f"Dry run complete. {total} change(s) would be made.")
    else:
        print(f"Done. {total} change(s) applied.")


if __name__ == '__main__':
    main()
