# Eval harness

Gold-set-based evaluation of the Allerjeez ingredient extraction + safety report pipeline.

## What we measure

- **Ingredient recall** — what % of the expected ingredients did Gemini find?
- **Ingredient precision** — what % of the extracted ingredients were really on the label?
- **Allergen recall** — what % of expected allergens were correctly flagged for the user? (The most important metric — false negatives on allergens are dangerous.)
- **Allergen precision** — what % of flagged allergens were real?
- **Latency** — p50 / p95 / p99 per scan
- **Cost** — avg Gemini calls per scan

## Folder structure

```
eval/
├── README.md             this file
├── gold_images/          25 food product images we hand-labeled
├── gold_labels.jsonl     one JSON object per image, ground truth
├── run_eval.py           the runner script
└── results.md            measured metrics, updated each eval run
```

## Gold set size: 25

A deliberate choice. Big enough that one bad scan doesn't dominate the metric (4% swing per scan); small enough to label realistically. Larger eval sets (~100+) are for production teams; 25 is the right portfolio scale.

## Gold label format

Each line of `gold_labels.jsonl` is a JSON object:

```json
{
  "image": "gold_images/snickers_01.jpg",
  "product_name": "Snickers",
  "expected_ingredients": ["sugar", "milk solids", "cocoa butter", "peanuts", ...],
  "expected_allergens": ["milk", "peanuts", "soy"],
  "expected_carcinogens": [],
  "notes": "Indian variant with E322 emulsifier annotation"
}
```

## How to run

```
uv run python -m eval.run_eval
```

Prints per-image results and an aggregate metrics table. Writes results to `eval/results.md` with timestamp.
