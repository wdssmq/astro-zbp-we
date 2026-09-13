import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path


DATA_URL = "https://github.com/wdssmq/Z-Blog-We/raw/refs/heads/main/data/issues/all.json"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "src/content/issues"


def fetch_records():
    request = urllib.request.Request(
        DATA_URL,
        headers={"User-Agent": "astro-zbp-we-data-sync/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)

    if not isinstance(payload, list):
        raise ValueError("远程数据必须是 JSON 数组")
    return payload


def clean_text(value):
    return str(value or "").strip()


def normalize_tags(value):
    if not isinstance(value, list):
        return []
    return [clean_text(item) for item in value if clean_text(item)]


def stable_id(record, index):
    source = clean_text(record.get("dedupe_key"))
    if not source:
        issue = record.get("issue")
        if isinstance(issue, dict):
            source = clean_text(issue.get("number"))
    if not source:
        source = json.dumps(record, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    record_type = clean_text(record.get("type")).lower() or "item"
    return f"{record_type}-{digest or index}"


def yaml_string(value):
    return json.dumps(clean_text(value), ensure_ascii=False)


def optional_yaml_string(value):
    value = clean_text(value)
    return yaml_string(value) if value else ""


def render_record(record, index):
    issue = record.get("issue") if isinstance(record.get("issue"), dict) else {}
    record_type = clean_text(record.get("type")).lower()
    if record_type not in {"rss", "app"}:
        raise ValueError(f"第 {index + 1} 条记录的 type 无效: {record_type!r}")

    name = clean_text(record.get("name"))
    description = clean_text(record.get("description"))
    if not name:
        raise ValueError(f"第 {index + 1} 条记录缺少 name")
    if not description:
        raise ValueError(f"第 {index + 1} 条记录缺少 description")

    rss_url = clean_text(record.get("rss_url"))
    git_repo_url = clean_text(record.get("git_repo_url"))
    canonical_url = clean_text(record.get("canonical_url"))
    issue_url = clean_text(issue.get("url"))
    issue_number = issue.get("number")
    lines = [
        "---",
        f"type: {yaml_string(record_type)}",
        f"name: {yaml_string(name)}",
        f"description: {yaml_string(description)}",
        "tags:",
    ]
    lines.extend(f"  - {yaml_string(tag)}" for tag in normalize_tags(record.get("tags")))
    for key, value in (
        ("rssUrl", rss_url),
        ("gitRepoUrl", git_repo_url),
        ("canonicalUrl", canonical_url),
        ("issueTitle", issue.get("title")),
        ("issueUrl", issue_url),
        ("updatedAt", issue.get("updated_at")),
        ("collectedAt", record.get("collected_at")),
    ):
        rendered = optional_yaml_string(value)
        if rendered:
            lines.append(f"{key}: {rendered}")
    if isinstance(issue_number, int):
        lines.append(f"issueNumber: {issue_number}")
    lines.extend(["---", "", description, ""])
    return "\n".join(lines)


def build_files(records, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"第 {index + 1} 条记录不是对象")
        filename = f"{stable_id(record, index)}.md"
        if filename in seen:
            raise ValueError(f"生成了重复文件名: {filename}")
        seen.add(filename)
        (output_dir / filename).write_text(
            render_record(record, index), encoding="utf-8"
        )


def replace_output(temp_dir):
    backup_dir = OUTPUT_DIR.with_name(f"{OUTPUT_DIR.name}.old")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    if OUTPUT_DIR.exists():
        OUTPUT_DIR.rename(backup_dir)
    try:
        Path(temp_dir).rename(OUTPUT_DIR)
    except Exception:
        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)
        if backup_dir.exists():
            backup_dir.rename(OUTPUT_DIR)
        raise
    if backup_dir.exists():
        shutil.rmtree(backup_dir)


def main():
    try:
        records = fetch_records()
        OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=OUTPUT_DIR.parent) as temp_dir:
            build_files(records, Path(temp_dir))
            replace_output(temp_dir)
        print(f"已生成 {len(records)} 个 issues Markdown 文件。")
        return 0
    except Exception as error:
        print(f"同步失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())