# /// script
# requires-python = ">=3.12"
# ///
"""Scrape model metadata and benchmark scores from vals.ai into CSV files."""

import csv
import gzip
import json
import random
import re
import sys
import time
import urllib.request
import urllib.robotparser
from pathlib import Path

SITE = "https://www.vals.ai"
ROBOTS = urllib.robotparser.RobotFileParser(SITE + "/robots.txt")
OUT = Path(__file__).parent / "data"
USER_AGENT = "vals-ai-indexer (+https://github.com/dot-mike/vals-ai-scrape)"
MODEL_FIELDS = {
    "label": r'label:"([^"]*)"',
    "company": r'company:"([^"]*)"',
    "country": r'country:"([^"]*)"',
    "release_date": r'release_date:"([^"]*)"',
    "open_source": r"open_source:(!0|!1)",
    "documentation_url": r'documentation_url:"([^"]*)"',
    "context_window": r"context_window:([\d.e]+)",
    "max_output_tokens": r"max_tokens:([\d.e]+)",
    "reasoning": r"reasoning_model:(!0|!1)",
    "images": r"images:(!0|!1)",
    "audio": r"audio:(!0|!1)",
    "videos": r"videos:(!0|!1)",
    "tools": r"tools:(!0|!1)",
    "deprecated": r"deprecated:(!0|!1)",
    "type": r'type:"([^"]*)"',
    "slug": r'slug:"([^"]*)"',
}
SCORE_FIELDS = ["accuracy", "stderr", "cost_per_test", "latency", "reasoning_effort"]


def get(path: str) -> str:
    """Fetch a vals.ai path, if robots.txt allows it."""
    if not ROBOTS.mtime():
        ROBOTS.read()
    if not ROBOTS.can_fetch(USER_AGENT, SITE + path):
        raise PermissionError(f"robots.txt disallows {path}")
    time.sleep(max(ROBOTS.crawl_delay(USER_AGENT) or 0, random.uniform(2, 5)))
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
    req = urllib.request.Request(SITE + path, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as res:
        body = res.read()
        if res.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        return body.decode("utf-8")


def find_constants_chunk() -> str:
    """Path of the JS chunk that holds the model registry."""
    page = get("/models")
    for component in sorted(
        set(re.findall(r'component-url="(/_astro/[\w.-]+\.js)"', page))
    ):
        found = re.search(r'from"\./(constants\.[\w-]+\.js)"', get(component))
        if found:
            return f"/_astro/{found.group(1)}"
    raise RuntimeError("no constants chunk found on /models")


def scrape_models() -> list[dict]:
    js = get(find_constants_chunk())
    starts = list(re.finditer(r'"([\w.-]+/[^"]+)":\{company:', js))
    models = []
    for i, start in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else start.start() + 8000
        entry = js[start.start() : end]
        row = {"id": start.group(1)}
        for field, pattern in MODEL_FIELDS.items():
            found = re.search(pattern, entry)
            value = found.group(1) if found else ""
            if field in ("context_window", "max_output_tokens") and value:
                # Minified JS writes 512000 as 512e3.
                value = str(int(float(value)))
            row[field] = {"!0": "true", "!1": "false"}.get(value, value)
        if row["type"] == "model":
            models.append(row)
    return models


def scrape_scores() -> list[dict]:
    sitemap = get("/sitemap.xml")
    slugs = sorted(set(re.findall(rf"<loc>{SITE}/benchmarks/([\w-]+)</loc>", sitemap)))
    rows = []
    for slug in slugs:
        try:
            page = get(f"/benchmarks/{slug}")
            found = re.search(r"/_astro/benchmark_view_[\w.-]+\.json", page)
            if not found:
                print(f"skip {slug}: no benchmark data", file=sys.stderr)
                continue
            view = json.loads(get(found.group(0)))
        except PermissionError as e:
            print(f"skip {slug}: {e}", file=sys.stderr)
            continue
        meta = view["metadata"]
        for task, results in view["tasks"].items():
            scored = [m for m, r in results.items() if r.get("accuracy") is not None]
            for model, result in results.items():
                accuracy = result.get("accuracy")
                rank = (
                    1 + sum(results[m]["accuracy"] > accuracy for m in scored)
                    if accuracy is not None
                    else ""
                )
                rows.append(
                    {
                        "benchmark": slug,
                        "benchmark_name": meta.get("benchmark", slug),
                        "benchmark_updated": meta.get("updated", ""),
                        "industry": meta.get("industry", ""),
                        "task": task,
                        "task_name": meta.get("tasks", {}).get(task, task),
                        "model": model,
                        "rank": rank,
                        "ranked": len(scored),
                        **{f: result.get(f, "") for f in SCORE_FIELDS},
                    }
                )
    return rows


def write(name: str, rows: list[dict]) -> None:
    OUT.mkdir(exist_ok=True)
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def main() -> None:
    scores = scrape_scores()
    models = scrape_models()
    index = {
        s["model"]: s
        for s in scores
        if s["benchmark"] == "vals_index" and s["task"] == "overall"
    }
    for m in models:
        vi = index.get(m["id"], {})
        m["vals_index"] = vi.get("accuracy", "")
        m["vals_index_rank"] = vi.get("rank", "")
        m["vals_url"] = f"{SITE}/models/{m['slug']}" if m["slug"] else ""
    assert len(models) > 100, f"only {len(models)} models, the registry format changed"
    assert len({s["benchmark"] for s in scores}) > 20, (
        "too few benchmarks, the page format changed"
    )
    assert index, "no Vals Index scores"
    models.sort(key=lambda m: m["id"])
    scores.sort(key=lambda s: (s["benchmark"], s["task"], s["model"]))
    write("models.csv", models)
    write("scores.csv", scores)


if __name__ == "__main__":
    main()
