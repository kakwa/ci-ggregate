#!/usr/bin/env python3
"""
ci-ggregate: Aggregate CI badges from GitHub Actions workflows across orgs/users.
Updates README.md with a table of repositories and their CI status badges.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    print("Error: pyyaml is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

README_PATH = "README.md"
CONFIG_PATH = "config.yml"
START_MARKER = "<!-- CI_BADGES_START -->"
END_MARKER = "<!-- CI_BADGES_END -->"


def github_request(url, token=None):
    """Make a GitHub API GET request and return (data, next_page_url)."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "ci-ggregate/1.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            next_url = _parse_next_link(resp.headers.get("Link", ""))
            return data, next_url
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if e.code == 404:
            return None, None
        if e.code in (403, 429):
            print(f"  Warning: rate-limited or forbidden for {url} ({e.code})", file=sys.stderr)
            return None, None
        print(f"  Warning: HTTP {e.code} for {url}: {body[:200]}", file=sys.stderr)
        return None, None


def _parse_next_link(link_header):
    """Parse the 'next' URL from a GitHub Link header."""
    for part in link_header.split(","):
        url_part, *params = part.strip().split(";")
        if any('rel="next"' in p for p in params):
            return url_part.strip().strip("<>")
    return None


def get_all_pages(url, token=None):
    """Fetch all pages of a paginated GitHub list endpoint."""
    results = []
    current_url = url
    while current_url:
        data, next_url = github_request(current_url, token)
        if not isinstance(data, list):
            break
        results.extend(data)
        current_url = next_url
        if next_url:
            time.sleep(0.05)
    return results


def get_repos(owner, owner_type, token=None):
    """Return all non-archived, non-fork public repos for a user or org."""
    if owner_type == "user":
        url = f"https://api.github.com/users/{owner}/repos?type=public&per_page=100&sort=name"
    else:
        url = f"https://api.github.com/orgs/{owner}/repos?type=public&per_page=100&sort=name"
    return get_all_pages(url, token)


def get_workflows(owner, repo, token=None):
    """Return the list of workflow objects for a repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows"
    data, _ = github_request(url, token)
    if isinstance(data, dict):
        return data.get("workflows", [])
    return []


def make_badge(owner, repo, workflow_path, workflow_name):
    """Return the markdown for a single GitHub Actions status badge."""
    prefix = ".github/workflows/"
    wf_id = workflow_path[len(prefix):] if workflow_path.startswith(prefix) else workflow_path
    wf_url = f"https://github.com/{owner}/{repo}/actions/workflows/{wf_id}"
    badge_url = f"{wf_url}/badge.svg"
    return f"[![{workflow_name}]({badge_url})]({wf_url})"


def build_table(targets, token=None, skip_archived=True, skip_forks=True):
    """Scan targets and return the full markdown badge table as a string."""
    rows = []

    for target in targets:
        owner = target["owner"]
        owner_type = target.get("type", "user")
        t_skip_archived = target.get("skip_archived", skip_archived)
        t_skip_forks = target.get("skip_forks", skip_forks)

        print(f"Scanning {owner_type}: {owner} ...")
        repos = get_repos(owner, owner_type, token)

        for repo in sorted(repos, key=lambda r: r["name"].lower()):
            if t_skip_archived and repo.get("archived", False):
                continue
            if t_skip_forks and repo.get("fork", False):
                continue

            repo_name = repo["name"]
            repo_url = repo["html_url"]
            workflows = get_workflows(owner, repo_name, token)

            if not workflows:
                continue

            badges = " ".join(
                make_badge(owner, repo_name, wf["path"], wf["name"])
                for wf in workflows
            )
            rows.append(f"| [{owner}/{repo_name}]({repo_url}) | {badges} |")
            print(f"  + {owner}/{repo_name}  ({len(workflows)} workflow(s))")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = [
        f"_Last updated: {timestamp}_",
        "",
        "| Repository | CI Status |",
        "|:-----------|:----------|",
    ]
    if not rows:
        rows = ["| _(none found)_ | — |"]

    return "\n".join(header + rows)


def update_readme(table_md, readme_path=README_PATH):
    """Replace the badge section in README.md (or append it if absent)."""
    with open(readme_path) as f:
        content = f.read()

    new_section = f"{START_MARKER}\n{table_md}\n{END_MARKER}"

    if START_MARKER in content and END_MARKER in content:
        start = content.index(START_MARKER)
        end = content.index(END_MARKER) + len(END_MARKER)
        new_content = content[:start] + new_section + content[end:]
    else:
        new_content = content.rstrip() + "\n\n" + new_section + "\n"

    with open(readme_path, "w") as f:
        f.write(new_content)

    print("README.md updated.")


def load_config(path=CONFIG_PATH):
    if not os.path.exists(path):
        print(f"Config file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print(
            "Warning: GH_TOKEN not set — unauthenticated requests are limited to 60/hour.",
            file=sys.stderr,
        )

    config = load_config()
    targets = config.get("targets", [])
    if not targets:
        print("No targets found in config.yml.", file=sys.stderr)
        sys.exit(1)

    global_skip_archived = config.get("skip_archived", True)
    global_skip_forks = config.get("skip_forks", True)

    table = build_table(targets, token, global_skip_archived, global_skip_forks)
    update_readme(table)


if __name__ == "__main__":
    main()
