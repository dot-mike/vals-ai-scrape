# /// script
# requires-python = ">=3.12"
# ///
"""Check that get() refuses paths robots.txt disallows, without network."""

import scrape

scrape.ROBOTS.parse(["User-agent: *", "Disallow: /benchmarks/secret"])
for path in ("/benchmarks/secret", "/benchmarks/secret/x"):
    try:
        scrape.get(path)
    except PermissionError:
        continue
    raise AssertionError(f"{path} was fetched")
assert scrape.ROBOTS.can_fetch(scrape.USER_AGENT, scrape.SITE + "/benchmarks/ioi")
print("ok")
