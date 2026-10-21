# dynamical-systems

Doenet course at the University of Minnesota: a local mirror of Duane
Nykamp's Math 1241 course folder on [doenet.org](https://doenet.org)
("1241 converted",
[shared folder](https://doenet.org/sharedActivities/aM1EeELqDCwTamWnYKeTLe/5mqti6pRx4tEqQXjQgP1Fk)).

**This GitHub repo is the source of truth while the project is in
progress.** Collaborators edit the `.doenetml` files here, through normal
git branches and PRs. Doenet.org has no way for several people to edit the
same activity, so nobody edits the hosted copies directly. When the project
is finished, Duane pushes the repo's content back to Doenet.org (see
[Publishing back to Doenet.org](#publishing-back-to-doenetorg)).

## Layout

- `Math 1241/` mirrors the Doenet.org folder tree, with one `.doenetml`
  file per activity. Each **problem set** becomes a subfolder named after
  it, holding one file per problem. `doenet-sync.json` names the source
  folder.
- `scripts/` holds the pull/push tools, shared with `PreCalculus_Library`.

Each file starts with a tool-managed block:

```
<!-- Doenet-Sync
Doenet-Sync-ID: 7CeXK39y9zqetftKJHjydr
Doenet-Sync-Version: 0.7.28
Doenet-Sync-NumVariants: 1
Doenet-Sync-Hash: 3f9a1c7e12ab04de
-->
```

Don't hand-edit this block, and don't merge two files' blocks. The ID is how
the file finds its way back to the right activity. Everything below the
block is normal editing territory. The block is never sent to Doenet.org.
Renaming or moving a file is fine, because the ID travels with it.

## Setup

```
cp .env.example .env
# then edit .env and paste in a fresh connect.sid cookie value (see .env.example)
```

## Refreshing from Doenet.org

Run this only when the hosted copy has changed, for example if Duane edited
something there:

```
python3 scripts/doenet_pull.py --dry-run   # preview
python3 scripts/doenet_pull.py
```

Pull creates new files and updates unedited ones in place. It **never
overwrites a file that has been edited here**: those files are listed at the
end as "skipped" instead. Commit the result like any other change.

## Publishing back to Doenet.org

Only the folder's owner can save these activities on Doenet.org. With
anyone else's cookie, `doenet_push.py` reports each file as `READ-ONLY` and
sends nothing. When the project is done, Duane clones this repo, puts *his*
cookie in `.env`, and runs:

```
python3 scripts/doenet_push.py --all --dry-run   # preview what would push
python3 scripts/doenet_push.py --all
```

Push re-checks each activity on Doenet.org first. If an activity changed
there after the last pull, that file is skipped with `CONFLICT`. Re-run
pull, which reports the file as skipped because of local edits, reconcile
the two by hand, then push with `--force`.

## Known limitations

- Only documents are mirrored. **Images** (9 in the folder) and
  problem-set settings (item order, shuffle, repeats) stay on Doenet.org
  only, and push never changes them. Within a problem-set folder, files sort
  alphabetically, not in problem-set order.
- Each problem is pushed individually by its ID. Adding a new file, or
  adding or removing a problem in a problem set, has to be done on
  Doenet.org.
- `numVariants` is carried over as-is on push, not recomputed. If an edit
  changes the variant count, check it in the Doenet editor afterward.
- Duplicate names in the same folder get a ` - <id prefix>` suffix (e.g.
  the many `Untitled Activity - 84EvLy.doenetml`).
- Session cookies expire. Refresh `.env` when pull starts failing with an
  auth-looking error.
