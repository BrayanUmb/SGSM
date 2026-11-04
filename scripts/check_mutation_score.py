"""Fail the build when the mutation score is below the threshold.

Usage: python scripts/check_mutation_score.py [threshold_percent]
Reads the mutants/ directory produced by `mutmut run` through `mutmut results --all true`.
"""
import re
import subprocess
import sys

THRESHOLD = float(sys.argv[1]) if len(sys.argv) > 1 else 50.0


def main():
    out = subprocess.run(
        ["mutmut", "results", "--all", "true"], capture_output=True, text=True, check=True
    ).stdout
    counts = {"killed": 0, "survived": 0, "timeout": 0, "suspicious": 0, "no tests": 0}
    for line in out.splitlines():
        m = re.search(r":\s*(killed|survived|timeout|suspicious|no tests)\s*$", line)
        if m:
            counts[m.group(1)] += 1
    total = sum(counts.values())
    if total == 0:
        sys.exit("No mutants found: did `mutmut run` execute?")
    caught = counts["killed"] + counts["timeout"]
    score = 100.0 * caught / total
    print(f"Mutants: {total} | killed: {counts['killed']} | survived: {counts['survived']}"
          f" | timeout: {counts['timeout']} | suspicious: {counts['suspicious']}")
    print(f"Mutation score: {score:.2f}% (threshold {THRESHOLD:.0f}%)")
    if score < THRESHOLD:
        sys.exit(f"FAIL: mutation score below {THRESHOLD:.0f}%")


if __name__ == "__main__":
    main()
