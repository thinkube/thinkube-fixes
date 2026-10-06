# thinkube-fixes

News and fixes for installed Thinkube clusters.

Thinkube Control reads this repository when it starts and every six hours.
It shows what it finds on its **News & Fixes** page, with a count in the top
bar. When you click **Apply** on a fix, Thinkube Control updates the
component on your cluster. Nothing is applied without that click.

## What a cluster reads

One file per platform release, on the `main` branch:

```
releases/0.1.json    read by every Thinkube 0.1 cluster
```

Each file has two lists, `news` and `fixes`. Every field is required.
`schema/feed.schema.json` is the exact format.

A **news** entry:

```json
{
  "id": "thinkube-0-1-0",
  "date": "2026-10-20",
  "title": "Thinkube 0.1.0",
  "body": "Plain text. A blank line starts a new paragraph."
}
```

A **fix** entry:

```json
{
  "id": "valkey-test-password",
  "date": "2026-10-21",
  "title": "The Valkey test uses the password",
  "body": "What was wrong, and what changes on your cluster when you apply it.",
  "severity": "bug",
  "component": "valkey",
  "kind": "optional",
  "fixed_in": "0.1.1",
  "commit": "<the 40-character commit on release-0.1 of thinkube/thinkube>",
  "playbook": "ansible/40_thinkube/optional/valkey/00_install.yaml"
}
```

- `severity` is `security` or `bug`. Security fixes are listed first.
- `component` is the component's name as Thinkube Control shows it.
- `fixed_in` is the component version that contains the fix.
- `commit` is a commit on the release branch of
  [thinkube/thinkube](https://github.com/thinkube/thinkube).
- `playbook` is the playbook that installs the component, in that repository.
  The one exception is `thinkube-control`: its install playbook,
  `12_deploy.yaml`, drops the component's databases, so a fix of
  thinkube-control names
  `ansible/40_thinkube/core/thinkube-control/12_deploy_dev.yaml`, which
  updates an installed Thinkube Control. The check refuses any other
  playbook for it.

## A fix is a pointer, not code

This repository holds no code that runs on a cluster. A fix entry only
names a commit of `thinkube/thinkube`. When you apply it, Thinkube Control:

1. moves its copy of `thinkube/thinkube` forward to the release branch,
   which contains that commit. It only moves forward. If the copy has
   changes that block a fast-forward, the run stops with git's message and
   nothing is changed;
2. runs the component's playbook from that copy;
3. reads the new component version, and then shows the fix as applied.

A fix of Thinkube Control itself cannot be applied by Thinkube Control,
because the update restarts it. The page shows the command to run in a
Thinkube IDE terminal instead.

A fix shows only on clusters where the component is installed, and only
while the installed version is older than `fixed_in`.

## Publishing a fix

1. Commit the fix to `release-0.1` of the component's repository.
2. Raise the `PATCH` of the component's `VERSION` file in the same branch,
   for example `0.1.0` to `0.1.1`.
3. Add an entry to `releases/0.1.json` here, and push.

The check in `.github/workflows/check.yaml` runs on every push. It fails
when the file does not follow the schema, when an `id` is used twice, when
the commit is not on `release-0.1`, when the playbook does not exist at that
commit, or when the `VERSION` next to the playbook does not say `fixed_in`.
Thinkube Control refuses a whole file when one entry is wrong, so a failed
check must be fixed at once: until then, no cluster sees any entry.

To run the check yourself:

```bash
git clone --no-checkout --filter=blob:none https://github.com/thinkube/thinkube.git /tmp/thinkube
git -C /tmp/thinkube fetch origin '+refs/heads/release-*:refs/remotes/origin/release-*'
pip install jsonschema
python scripts/check_feed.py /tmp/thinkube
```

## License

Apache-2.0. See [LICENSE](LICENSE).
