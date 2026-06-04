# Allerjeez extraction eval - results

_Run at_: `2026-06-04T12:34:01+00:00`

_Gold set size_: **25** images (20 scored)


## Aggregate metrics

| Metric | Value |
|---|---|
| Ingredient recall | **99.2%** |
| Ingredient precision | 99.4% |
| Ingredient F1 | 99.2% |
| **Allergen recall** | **77.7%** |
| Latency p50 | 9.78s |
| Latency p95 | 14.80s |
| Latency p99 | 16.13s |

## Per-image results

| Image | Recall | Precision | F1 | Allergen recall | Missed allergens |
|---|---|---|---|---|---|
| gold_images/aloo_bhujia.jpg | 100% | 100% | 100% | 100% | — |
| gold_images/applesauce.jpg | 100% | 100% | 100% | 100% | — |
| gold_images/boost.jpg | 100% | 100% | 100% | 100% | — |
| gold_images/bounty.jpg | 100% | 100% | 100% | 50% | soy |
| gold_images/chewing_gum.jpg | 100% | 100% | 100% | 0% | soy |
| gold_images/chocolate_syrup.jpg | 100% | 100% | 100% | 100% | — |
| gold_images/cup_noodles.jpg | 100% | 100% | 100% | 20% | wheat, gluten, eggs, milk |
| gold_images/dairymilk.jpg | 83% | 100% | 91% | 100% | — |
| gold_images/diet_coke.jpg | 100% | 100% | 100% | 100% | — |
| gold_images/frooti.jpg | 100% | 100% | 100% | 100% | — |
| gold_images/garam_masala.jpg | 100% | 100% | 100% | 100% | — |
| gold_images/granola.jpg | 100% | 88% | 93% | 67% | tree-nuts |
| gold_images/jam.jpg | 100% | 100% | 100% | 100% | — |
| gold_images/ketchup.jpg | _skipped_ | | | |  |
| gold_images/kitkat.jpg | _skipped_ | | | |  |
| gold_images/kurkure.jpg | _skipped_ | | | | All connection attempts failed |
| gold_images/lays.jpg | 100% | 100% | 100% | 100% | — |
| gold_images/maggi.jpg | 100% | 100% | 100% | 100% | — |
| gold_images/mayonnaise.jpg | 100% | 100% | 100% | 50% | soy |
| gold_images/mustard_sauce.jpg | 100% | 100% | 100% | 100% | — |
| gold_images/nutella.jpg | 100% | 100% | 100% | 33% | tree-nuts, soy |
| gold_images/oyster_sauce.jpg | 100% | 100% | 100% | 33% | gluten, shellfish |
| gold_images/redbull.jpg | 100% | 100% | 100% | 100% | — |
| gold_images/strawberry_yogurt.jpg | _skipped_ | | | | 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-2.5-flash\nPlease retry in 18.044916869s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'model': 'gemini-2.5-flash', 'location': 'global'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '18s'}]}} |
| gold_images/yakult.jpg | _skipped_ | | | | 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-2.5-flash\nPlease retry in 56.095966345s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-flash'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '56s'}]}} |
