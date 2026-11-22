from __future__ import annotations

import json
import os
import re
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

README_PATH = Path("README.md")
START_MARKER = "<!-- AUTO-STATS:START -->"
END_MARKER = "<!-- AUTO-STATS:END -->"


def fetch_repositories(username: str, token: str | None = None) -> list[dict]:
    """Fetch owned public repositories sorted by most recently updated."""
    url = (
        f"https://api.github.com/users/{username}/repos"
        "?per_page=100&sort=updated&type=owner"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-readme-updater",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        repos: list[dict] = json.loads(response.read().decode("utf-8"))

    return [
        repo
        for repo in repos
        if not repo.get("fork") and repo["name"].lower() != username.lower()
    ]


def build_markdown(repos: list[dict]) -> str:
    """Format repository statistics and recent projects into Markdown."""
    total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    languages = Counter(repo["language"] for repo in repos if repo.get("language"))
    top_langs = ", ".join(
        f"**{lang}** ({count})" for lang, count in languages.most_common(5)
    ) or "N/A"

    lines = [
        f"- **Public Original Repos:** {len(repos)}",
        f"- **Total Stars:** {total_stars}",
        f"- **Top Languages:** {top_langs}",
        "",
        "### Recently Updated Projects",
        "",
        "| Repository | Language | Stars | Last Updated |",
        "| :--- | :--- | :---: | :---: |",
    ]

    for repo in repos[:5]:
        name = repo["name"]
        url = repo["html_url"]
        lang = repo.get("language") or "—"
        stars = repo.get("stargazers_count", 0)
        updated = repo["pushed_at"][:10]
        lines.append(f"| [{name}]({url}) | {lang} | {stars} | {updated} |")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"\n<sub>Auto-updated daily via GitHub Actions • Last sync: {timestamp}</sub>")
    return "\n".join(lines)


def update_readme(new_section: str) -> None:
    """Replace content strictly between the two HTML comment markers."""
    content = README_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"({re.escape(START_MARKER)}).*?({re.escape(END_MARKER)})",
        re.DOTALL,
    )
    if not pattern.search(content):
        raise ValueError(
            f"Markers {START_MARKER} and {END_MARKER} not found in {README_PATH}."
        )

    updated = pattern.sub(
        lambda match: f"{match.group(1)}\n{new_section}\n{match.group(2)}",
        content,
        count=1,
    )
    README_PATH.write_text(updated, encoding="utf-8")


def main() -> None:
    username = os.environ.get("GITHUB_REPOSITORY_OWNER")
    if not username:
        raise EnvironmentError("Set the GITHUB_REPOSITORY_OWNER environment variable.")

    token = os.environ.get("GITHUB_TOKEN")
    repos = fetch_repositories(username, token)
    update_readme(build_markdown(repos))


if __name__ == "__main__":
    main()