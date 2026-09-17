#!/usr/bin/env python3
"""
Generates the standalone Frame Card Practice app by baking a CSV card set
into app_template.html. The CSV is read only at generation time; the
output HTML has no runtime CSV/file-loading step.

Usage:
    python3 generate_app.py <input_csv> <output_html>

CSV columns required: cardType, correct, plus any number of distractor
columns named D1, D2, D3, ... (case-insensitive, any count — the script
detects however many are present). Each row's distractor columns are
collapsed into a single deduplicated "distractors" list in the output;
blanks, non-integers, duplicates, and any value equal to "correct" are
dropped automatically. Distractor order is not preserved or meaningful.

An optional questionID column is allowed but not used.
"""
import csv
import json
import re
import sys
from datetime import datetime, timezone

VALID_TYPES = {
    "fiveframe": {"max": 5},
    "tenframe": {"max": 10},
    "doubletenframe": {"max": 20},
}

DISTRACTOR_COL_PATTERN = re.compile(r"^d\d+$")


def build_pool(csv_path):
    pool = {"fiveframe": [], "tenframe": [], "doubletenframe": []}
    errors = []

    # utf-8-sig strips a leading BOM if present, so "questionID" (not "\ufeffquestionID")
    # is what actually shows up as the first header key.
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]
        distractor_cols = [h for h in reader.fieldnames if DISTRACTOR_COL_PATTERN.match(h)]
        if not distractor_cols:
            print("Warning: no distractor columns (D1, D2, ...) found in header.")

        for row_num, row in enumerate(reader, start=2):  # header is row 1
            row = { (k or "").strip().lower(): (v or "").strip() for k, v in row.items() }
            card_type = row.get("cardtype", "").lower()
            if card_type not in VALID_TYPES:
                errors.append(f"Row {row_num}: invalid cardType \"{row.get('cardtype','')}\"")
                continue

            try:
                correct = int(row.get("correct", ""))
            except ValueError:
                errors.append(f"Row {row_num}: invalid correct value \"{row.get('correct','')}\"")
                continue

            if correct < 0 or correct > VALID_TYPES[card_type]["max"]:
                errors.append(
                    f"Row {row_num}: correct value {correct} out of range for {card_type} "
                    f"(0-{VALID_TYPES[card_type]['max']})"
                )
                continue

            distractors = []
            seen = set()
            for col in distractor_cols:
                raw = row.get(col, "")
                if raw == "":
                    continue
                try:
                    n = int(raw)
                except ValueError:
                    errors.append(f"Row {row_num}: non-integer distractor \"{raw}\" in {col} (skipped)")
                    continue
                if n == correct or n in seen:
                    continue
                seen.add(n)
                distractors.append(n)

            pool[card_type].append({
                "cardType": card_type,
                "correct": correct,
                "distractors": distractors,
            })

    return pool, errors


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 generate_app.py <input_csv> <output_html>")
        sys.exit(1)

    csv_path, output_path = sys.argv[1], sys.argv[2]

    pool, errors = build_pool(csv_path)

    if errors:
        print(f"{len(errors)} row(s) skipped:")
        for e in errors:
            print("  -", e)

    counts = {k: len(v) for k, v in pool.items()}
    print("Card counts:", counts)

    with open("app_template.html", encoding="utf-8") as f:
        template = f.read()

    pool_json = json.dumps(pool)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    source_file = json.dumps(csv_path.split("/")[-1])

    html = template
    html = html.replace(
        '/*__QUESTION_POOL__*/{}/*__END_QUESTION_POOL__*/',
        pool_json
    )
    html = html.replace(
        '/*__GENERATED_AT__*/"unknown"/*__END_GENERATED_AT__*/',
        json.dumps(generated_at)
    )
    html = html.replace(
        '/*__SOURCE_FILE__*/"unknown"/*__END_SOURCE_FILE__*/',
        source_file
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

