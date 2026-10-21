#!/usr/bin/env python3
"""Pull synced folders from Doenet.org into local files.

Usage:
    python3 scripts/doenet_pull.py [--dry-run]
    python3 scripts/doenet_pull.py --root "Math 1241" [--dry-run]

Without --root, every folder in this repo that has a doenet-sync.json is
pulled. A document already present locally (matched by its embedded
Doenet-Sync-ID) is updated IN PLACE at its existing path, even if its
name/folder changed on Doenet.org -- pull never renames a file you've
reorganized locally. A file with local edits that haven't been pushed yet
is left alone and reported at the end, rather than being overwritten.
Problem sets are expanded into a subfolder holding one file per document.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doenet_common as dc  # noqa: E402

REPO_ROOT = dc.REPO_ROOT


def build_local_index(folder):
    """contentId -> (path, sync_fields, stripped_body)"""
    index = {}
    for full_path in dc.find_doenetml_files(folder):
        with open(full_path, "r", encoding="utf-8") as f:
            text = f.read()
        fields, stripped_body = dc.split_sync_header(text)
        if fields:
            index[fields["id"]] = (full_path, fields, stripped_body)
    return index


def mirror_path(folder, path_parts, name, content_id, claimed_paths):
    """Build the mirrored path, disambiguating if another activity (a
    different contentId) already claimed the same path this run or on disk
    -- two different Doenet activities can share the exact same name."""
    parts = [dc.sanitize_path_component(p) for p in path_parts]
    base_name = dc.sanitize_path_component(name)
    candidate = os.path.join(folder, *parts, base_name + ".doenetml")
    if candidate not in claimed_paths and not os.path.exists(candidate):
        return candidate
    suffix = content_id[:6]
    return os.path.join(folder, *parts, f"{base_name} - {suffix}.doenetml")


def pull_folder(folder, cookie, dry_run, counts, skipped_local_edits):
    config = dc.load_sync_config(folder)
    local_index = build_local_index(folder)
    print(f"=== {os.path.relpath(folder, REPO_ROOT)} ({len(local_index)} tracked locally) ===")

    claimed_paths = {entry[0] for entry in local_index.values()}

    def on_folder(path_parts):
        print(f"  scanning {' / '.join(path_parts) or '(top)'}...")

    def documents():
        for path_parts, item in dc.walk_folder(config["ownerId"], config["folderId"], cookie, on_folder=on_folder):
            if item.get("type") == "singleDoc":
                yield path_parts, item
            elif item.get("type") in ("sequence", "select"):
                yield from dc.expand_problem_set(path_parts, item, cookie)

    for path_parts, item in documents():

        content_id = item["contentId"]
        remote_body = item["doenetML"]
        remote_hash = dc.body_hash(remote_body)
        version = item["doenetmlVersion"]["fullVersion"]
        num_variants = item["numVariants"]

        if content_id in local_index:
            local_path, local_fields, local_stripped_body = local_index[content_id]
            local_current_hash = dc.body_hash(local_stripped_body)

            if local_current_hash != local_fields["hash"] and local_current_hash != remote_hash:
                skipped_local_edits.append(local_path)
                continue

            target_path = local_path
            if local_fields["hash"] == remote_hash and local_current_hash == remote_hash:
                counts["unchanged"] += 1
                continue
            is_new = False
        else:
            target_path = mirror_path(folder, path_parts, item["name"], content_id, claimed_paths)
            claimed_paths.add(target_path)
            is_new = True

        new_text = dc.insert_or_update_sync_block(
            remote_body, content_id, version, num_variants, remote_hash
        )

        if dry_run:
            print(f"  [dry-run] would {'create' if is_new else 'update'}: {os.path.relpath(target_path, REPO_ROOT)}")
        else:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(new_text)

        counts["created" if is_new else "updated"] += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", help="pull only this synced folder")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    folders = dc.find_synced_folders(args.root)
    if not folders:
        raise SystemExit(f"No folders with a {dc.SYNC_CONFIG_NAME} found in {REPO_ROOT}")
    cookie = dc.get_cookie()

    counts = {"created": 0, "updated": 0, "unchanged": 0}
    skipped_local_edits = []
    for folder in folders:
        pull_folder(folder, cookie, args.dry_run, counts, skipped_local_edits)

    print("\n=== Summary ===")
    for k, v in counts.items():
        print(f"  {k + ':':10} {v}")
    if skipped_local_edits:
        print(f"  skipped (local edits not yet pushed, NOT overwritten): {len(skipped_local_edits)}")
        for p in skipped_local_edits:
            print(f"    - {os.path.relpath(p, REPO_ROOT)}")


if __name__ == "__main__":
    main()
