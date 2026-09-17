# Frame Card Practice — Build & Generation Notes

Functional (black & white) mockup stage. Covers file purposes and the two
formulas embedded in the app: the no-repeat randomization logic and the
double ten-frame grid geometry.

---

## File breakdown

| File | Purpose |
|---|---|
| `app_template.html` | The app shell. Contains all UI, mode logic (Free Practice / Timed / Survival), card rendering, scoring, and the scorecard export — **plus** a placeholder (`/*__QUESTION_POOL__*/{}/*__END_QUESTION_POOL__*/`) where card data gets injected. Not meant to be opened directly with real data — it has an empty pool. Edit this file when you need to change app *behavior*. |
| `generate_app.py` | The build step. Reads a CSV, validates it, collapses each row's distractor columns into a single `distractors` list, and writes a new standalone HTML file with that data baked into a copy of `app_template.html`. Run this any time you have a new or updated CSV. |
| `frame_card_quiz_app.html` | Output of the generator — currently built from `Frame_Practice_Data.csv`. This is the file to actually hand to a student or open for testing. It has no file-upload step and no runtime CSV dependency; the data is a static JS object inside the file. |
| `sample_frame_card_set.csv` | Small 15-row placeholder set (5 cards per card type) used early on to validate the generator before real data existed. Safe to ignore now that `Frame_Practice_Data.csv` is in use — kept only as a minimal reference for the CSV column format. |
| `frame_card_quiz_mockup.html` | The very first version of this tool, before the generator/template split. Superseded — it still has the old in-browser "upload a CSV" flow. Kept for reference only; not part of the current workflow. |

### Regenerating the app

```
python3 generate_app.py <input_csv> <output_html>
```

Example:
```
python3 generate_app.py Frame_Practice_Data.csv frame_card_quiz_app.html
```

The script prints card counts per type and lists any skipped rows (invalid `cardType`, out-of-range `correct`, non-integer distractors) so bad data is caught at generation time rather than silently dropped at runtime.

### CSV format expected

| Column | Required | Notes |
|---|---|---|
| `cardType` | yes | `fiveframe`, `tenframe`, or `doubletenframe` |
| `correct` | yes | Integer within range for the type (0–5, 0–10, 0–20 respectively) |
| `D1`, `D2`, `D3`, ... | no | Any number of distractor columns, any naming like `D1`/`d1`. All get merged into one deduplicated `distractors` list per row — blanks, duplicates, non-integers, and any value equal to `correct` are dropped automatically. |
| `questionID` | no | Ignored by the generator; fine to leave in for your own tracking. |

---

## Formula notes

### 1. No-repeat-in-a-row randomization

This is the logic that selects which question comes next in all three modes, and it's designed to hold up regardless of pool size (5 cards or 5,000).

**Rule:** the `correct` value of the next question can never match the `correct` value of the question immediately before it.

Excel Formula: =LET(ct,$B2,mn,IFS(ct="fiveframe",0,ct="tenframe",0,ct="doubletenframe",10),mx,IFS(ct="fiveframe",5,ct="tenframe",10,ct="doubletenframe",20),correct,RANDBETWEEN(mn,mx),pool,SEQUENCE(mx-mn+1,1,mn),avail,FILTER(pool,pool<>correct),distractors,TAKE(SORTBY(avail,RANDARRAY(ROWS(avail))),3),HSTACK(correct,TRANSPOSE(distractors)))


```js
function pickRandomSource(cardType) {
  var pool = QUESTION_POOL[cardType];
  var candidates = pool.filter(q => q.correct !== lastCorrectValue);
  if (candidates.length === 0) candidates = pool; // only if every card shares one value
  var pick = candidates[Math.floor(Math.random() * candidates.length)];
  lastCorrectValue = pick.correct;
  return pick;
}
```

Free Practice uses the same rule to build a fixed 10-question queue up front (`buildNoRepeatQueue`), drawing with replacement if the pool has fewer than 10 cards.

**Scaling notes:**
- This only prevents *immediate* repeats of the correct value — it says nothing about the specific card (pattern/distractor set) shown, so two different rows sharing the same `correct` value elsewhere in the CSV are still fair game as long as they're not back-to-back.
- With a small pool (fewer than ~4–5 distinct `correct` values for a card type), the same handful of values will still resurface often — that's a pool-size issue, not a randomization bug. With your current 300-row set (99/100/101 cards per type, generally 6 distinct `correct` values per type — 0–5, 0–10, 10–20), repeats are spaced out much more naturally.
- The fallback (`if candidates.length === 0`) only triggers if every single card in a pool shares one `correct` value — worth keeping in mind if a future CSV is ever filtered down that far for a specific drill.

### 2. Double ten-frame grid gap

The two grids in a double ten-frame card are positioned using:

```
bottom_grid_y0 = top_grid_y0 + (rows × cellHeight) + gap
                = 46 + (2 × 46) + 18
                = 156
```

If the double ten-frame's cell height or row count ever changes, recompute `bottom_grid_y0` with this formula rather than hardcoding a new number — that's what caused the original zero-gap bug (the spec doc's table listed `y0=138`, which is the formula *without* the 18px gap term, contradicting its own stated design intent of two visually separate grids).
