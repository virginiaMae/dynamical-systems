#!/usr/bin/env python3
"""Push edited .doenetml files back to their matching activity on Doenet.org.

Usage:
    python3 scripts/doenet_push.py path/to/file.doenetml [path2 ...]
    python3 scripts/doenet_push.py --all [--root "Math 1241"]
    python3 scripts/doenet_push.py --all --dry-run
    python3 scripts/doenet_push.py path/to/file.doenetml --force

--all scans every synced folder (or just --root). Only the four
Doenet-Sync-* lines are used for bookkeeping locally; they are NEVER sent
to Doenet.org -- only the real DoenetML body is pushed, so the hosted
source stays exactly what it would look like if edited on the website.
Files in a synced folder owned by another account are skipped (READ-ONLY):
Doenet.org only lets an activity's owner save it.

Before pushing a file, the current remote content is re-fetched and compared
against the hash recorded at the last pull/push. If it has changed on
Doenet.org since then (someone edited it on the website), the push for that
file is aborted with a clear message -- pass --force to overwrite anyway.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doenet_common as dc  # noqa: E402

REPO_ROOT = dc.REPO_ROOT


def push_one(path, cookie, dry_run, force):
    rel = os.path.relpath(path, REPO_ROOT)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    fields, stripped_body = dc.split_sync_header(text)
    if not fields:
        print(f"SKIP  {rel} -- no Doenet-Sync-ID header, not a tracked file (created locally? not yet supported)")
        return "skip"

    current_hash = dc.body_hash(stripped_body)
    if current_hash == fields["hash"]:
        return "unchanged"

    if not force:
        remote = dc.get(f"activityEditView/getContentSource/{fields['id']}", cookie)
        remote_source = remote.get("source")
        if remote_source is None:
            print(f"ERROR {rel} -- could not fetch current remote content for conflict check")
            return "error"
        if dc.body_hash(remote_source) != fields["hash"]:
            print(
                f"CONFLICT {rel} -- this activity changed on Doenet.org since your "
                f"last pull/push. Re-run doenet_pull.py first, or re-run push with --force "
                f"to overwrite the remote copy anyway."
            )
            return "conflict"

    if dry_run:
        print(f"[dry-run] would push {rel}")
        return "would-push"

    status, body = dc.post(
        "updateContent/saveDoenetML",
        {
            "contentId": fields["id"],
            "doenetML": stripped_body,
            "numVariants": int(fields["numvariants"]),
        },
        cookie,
    )
    if status != 200:
        print(f"ERROR {rel} -- push failed ({status}): {body}")
        return "error"

    new_text = dc.insert_or_update_sync_block(
        stripped_body, fields["id"], fields["version"], fields["numvariants"], current_hash
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"PUSHED {rel}")
    return "pushed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--root", help="with --all, scan only this synced folder")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.all and not args.paths:
        print("Provide file path(s), or use --all to scan every synced folder.")
        sys.exit(1)

    if args.all:
        targets = [p for folder in dc.find_synced_folders(args.root) for p in dc.find_doenetml_files(folder)]
    else:
        targets = [os.path.abspath(p) for p in args.paths]
    cookie = dc.get_cookie()
    my_user_id = dc.get_my_user_id(cookie)

    counts = {}
    for path in targets:
        folder = dc.synced_folder_for(path)
        if folder and dc.load_sync_config(folder)["ownerId"] != my_user_id:
            # Doenet.org only lets the owner save an activity.
            print(f"READ-ONLY {os.path.relpath(path, REPO_ROOT)} -- {os.path.relpath(folder, REPO_ROOT)} is owned by another account")
            result = "read-only"
        else:
            result = push_one(path, cookie, args.dry_run, args.force)
        counts[result] = counts.get(result, 0) + 1

    print("\n=== Summary ===")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
