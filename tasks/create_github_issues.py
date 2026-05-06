from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "tasks" / "github-issues.md"

LABELS = {
    "ready-for-agent": ("0e8a16", "Fully specified and ready for an implementation agent."),
    "needs-triage": ("fbca04", "Maintainer needs to evaluate or refine this issue."),
    "area:artifacts": ("5319e7", "Artifact contracts, manifests, hashes, and indexes."),
    "area:backend": ("1d76db", "Backend implementation."),
    "area:ci": ("0b7285", "Continuous integration and release checks."),
    "area:cli": ("0052cc", "Command-line interface."),
    "area:docs": ("0075ca", "Documentation and source-of-truth updates."),
    "area:evidence": ("6f42c1", "Evidence, grounding, and ClaimRefs."),
    "area:evaluation": ("c5def5", "Evaluation and regression harnesses."),
    "area:frontend": ("bfd4f2", "Frontend UI and product shell."),
    "area:mirofish": ("d4c5f9", "MiroFish integration."),
    "area:observability": ("c2e0c6", "Telemetry, logs, and operational visibility."),
    "area:ops": ("bfdadc", "Runtime operations and deployment behavior."),
    "area:permissions": ("fef2c0", "Roles, access control, and export permissions."),
    "area:risk-pack": ("d876e3", "Risk pack authoring and versioned templates."),
    "area:security": ("ee0701", "Security, privacy, and safety controls."),
    "area:verdict-council": ("b60205", "Verdict Council product services and gates."),
    "priority:p0": ("b60205", "Critical MVP blocker."),
    "priority:p1": ("d93f0b", "Important MVP work."),
    "priority:p2": ("fbca04", "Post-MVP or lower urgency."),
    "mvp": ("0e8a16", "Required for MVP definition of done."),
    "post-mvp": ("cfd3d7", "Targeted after MVP stabilization."),
}


def gh(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        cwd=ROOT,
        text=True,
        input=input_text,
        capture_output=True,
        check=False,
    )


def parse_issues(markdown: str) -> list[dict[str, str | list[str]]]:
    matches = list(re.finditer(r"^###\s+\d+\.\s+(.+)$", markdown, re.MULTILINE))
    issues: list[dict[str, str | list[str]]] = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        section = markdown[start:end].strip()

        labels_match = re.search(r"^Labels:\s+(.+)$", section, re.MULTILINE)
        if not labels_match:
            raise ValueError(f"missing labels for {title}")
        labels = re.findall(r"`([^`]+)`", labels_match.group(1))

        body_start = section.find("Dependencies:")
        if body_start == -1:
            body_start = section.find("Body:")
        body = section[body_start:].strip()
        body = body.replace("\nBody:\n", "\n", 1)
        body = body.replace("Body:\n", "", 1)

        issues.append({"title": title, "labels": labels, "body": body})
    return issues


def ensure_labels() -> None:
    result = gh("label", "list", "--limit", "200", "--json", "name")
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    existing = {row["name"] for row in json.loads(result.stdout)}
    for name, (color, description) in LABELS.items():
        if name in existing:
            continue
        created = gh("label", "create", name, "--color", color, "--description", description)
        if created.returncode != 0:
            sys.stderr.write(created.stderr)
            raise SystemExit(created.returncode)
        print(f"created label: {name}")


def existing_issue_titles() -> set[str]:
    result = gh("issue", "list", "--state", "all", "--limit", "200", "--json", "title")
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return {row["title"] for row in json.loads(result.stdout)}


def create_issues(issues: list[dict[str, str | list[str]]]) -> None:
    existing = existing_issue_titles()
    for issue in issues:
        title = str(issue["title"])
        labels = list(issue["labels"])
        body = str(issue["body"])
        if title in existing:
            print(f"skipped existing issue: {title}")
            continue
        args = ["issue", "create", "--title", title, "--body", body]
        for label in labels:
            args.extend(["--label", label])
        created = gh(*args)
        if created.returncode != 0:
            sys.stderr.write(created.stderr)
            raise SystemExit(created.returncode)
        print(f"created issue: {title} -> {created.stdout.strip()}")


def main() -> int:
    issues = parse_issues(BACKLOG.read_text(encoding="utf-8"))
    ensure_labels()
    create_issues(issues)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
