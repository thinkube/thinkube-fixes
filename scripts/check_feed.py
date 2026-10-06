#!/usr/bin/env python3
# Copyright Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
Check every feed in releases/ before it reaches a cluster.

For releases/<MAJOR.MINOR>.json:
- the file follows schema/feed.schema.json;
- every id, news and fix together, is used once;
- each fix's commit is on branch release-<MAJOR.MINOR> of thinkube/thinkube;
- at that commit, the playbook exists, and the VERSION file in its directory
  says fixed_in, with the release's MAJOR.MINOR.

Thinkube Control refuses a whole feed when one entry is wrong, so a mistake
here would hide every entry from every cluster of that release.

Usage: scripts/check_feed.py [thinkube-checkout]
The checkout is a clone of thinkube/thinkube with its release branches
fetched; it is needed only when a feed has fixes.
"""

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTROL_UPDATE_PLAYBOOK = "ansible/40_thinkube/core/thinkube-control/12_deploy_dev.yaml"


def git(checkout: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(checkout), *args], capture_output=True, text=True)


def check(feed_path: Path, validator: Draft202012Validator, checkout: Path | None) -> list[str]:
    release = feed_path.stem
    errors = []
    try:
        feed = json.loads(feed_path.read_text())
    except ValueError as e:
        return [f"{feed_path.name}: not valid JSON: {e}"]

    for error in validator.iter_errors(feed):
        where = "/".join(str(p) for p in error.absolute_path) or "(top)"
        errors.append(f"{feed_path.name}: {where}: {error.message}")
    if errors:
        return errors

    seen = set()
    for entry in feed["news"] + feed["fixes"]:
        if entry["id"] in seen:
            errors.append(f"{feed_path.name}: id '{entry['id']}' is used twice")
        seen.add(entry["id"])

    if feed["fixes"] and checkout is None:
        return errors + [f"{feed_path.name}: has fixes; pass a thinkube checkout to check them"]

    branch = f"origin/release-{release}"
    for fix in feed["fixes"]:
        where = f"{feed_path.name}: fix '{fix['id']}'"
        if not fix["fixed_in"].startswith(f"{release}."):
            errors.append(f"{where}: fixed_in {fix['fixed_in']} is not a {release} version")
        if not fix["playbook"].startswith(f"ansible/40_thinkube/{fix['kind']}/"):
            errors.append(f"{where}: playbook is not under ansible/40_thinkube/{fix['kind']}/")
        if ".." in fix["playbook"]:
            errors.append(f"{where}: playbook path contains '..'")
        # thinkube-control's install playbook, 12_deploy.yaml, drops the
        # component's databases; a cluster updates it with 12_deploy_dev.yaml.
        if fix["component"] == "thinkube-control" and fix["playbook"] != CONTROL_UPDATE_PLAYBOOK:
            errors.append(f"{where}: a thinkube-control fix names {CONTROL_UPDATE_PLAYBOOK}")
        on_branch = git(checkout, "merge-base", "--is-ancestor", fix["commit"], branch)
        if on_branch.returncode != 0:
            errors.append(f"{where}: commit {fix['commit']} is not on {branch}: {on_branch.stderr.strip()}")
            continue
        playbook = git(checkout, "cat-file", "-e", f"{fix['commit']}:{fix['playbook']}")
        if playbook.returncode != 0:
            errors.append(f"{where}: {fix['playbook']} does not exist at {fix['commit']}")
            continue
        version_path = str(Path(fix["playbook"]).parent / "VERSION")
        version = git(checkout, "show", f"{fix['commit']}:{version_path}")
        if version.returncode != 0:
            errors.append(f"{where}: {version_path} does not exist at {fix['commit']}")
        elif version.stdout.strip() != fix["fixed_in"]:
            errors.append(
                f"{where}: {version_path} at {fix['commit']} is {version.stdout.strip()}, not {fix['fixed_in']}"
            )
    return errors


def main() -> int:
    checkout = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    validator = Draft202012Validator(json.loads((ROOT / "schema" / "feed.schema.json").read_text()))
    feeds = sorted((ROOT / "releases").glob("*.json"))
    if not feeds:
        print("No feed in releases/")
        return 1
    errors = []
    for feed_path in feeds:
        errors += check(feed_path, validator, checkout)
    for error in errors:
        print(f"ERROR: {error}")
    if not errors:
        print(f"OK: {', '.join(p.name for p in feeds)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
