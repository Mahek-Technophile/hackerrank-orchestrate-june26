# Multimodal Damage-Claim Verification System

## Executive Summary

This solution implements a competition-ready claim verification pipeline for the HackerRank Orchestrate multimodal evidence review challenge. It combines:

- deterministic claim parsing from the conversation transcript
- image-level multimodal evidence review through a provider abstraction
- a rule-based evidence aggregation and contradiction engine
- a separate fraud and manual-review risk layer
- an evaluation workflow with reproducible metrics and reporting

The design is optimized for leaderboard performance and AI Judge defensibility:

- images remain the primary source of truth
- user history adds risk context but does not override clear visual evidence
- output generation is schema-locked and reproducible
- provider selection is configurable, enabling stronger hosted VLMs in production and an offline fallback for smoke tests

## Problem Understanding

Each row contains:

- one user conversation describing a damage claim
- one or more images
- a coarse object type: `car`, `laptop`, or `package`
- linked user-history data and evidence requirements

The system must decide whether the images:

- support the claim
- contradict the claim
- do not provide enough information

It must also produce:

- `evidence_standard_met`
- `risk_flags`
- `issue_type`
- `object_part`
- `supporting_image_ids`
- `valid_image`
- `severity`

## Recommended Final Architecture

```text
CSV Loader
  -> Claim Parser
  -> Evidence Requirement Attachment
  -> Image Review Provider (OpenAI recommended for final run)
  -> Evidence Aggregator
  -> Risk Layer
  -> Decision Engine
  -> Output CSV Writer
  -> Evaluation + Error Analysis
```

## Data Flow Design

1. Read `claims.csv`, `user_history.csv`, and `evidence_requirements.csv`.
2. Parse the conversation into structured claim facets.
3. Review each image separately through a vision provider.
4. Aggregate image evidence at the claim level.
5. Apply risk flags from image quality, authenticity, conversation injections, and user history.
6. Write schema-compliant `output.csv`.
7. Evaluate on `sample_claims.csv`.

## Multimodal Reasoning Framework

The reasoning stack is intentionally staged instead of monolithic:

1. `Claim parsing`
   Extracts the final requested review target from the conversation, including multilingual inputs and multi-part mentions.
2. `Image review`
   Evaluates each image independently to reduce multi-image leakage and improve supporting-image selection.
3. `Aggregation`
   Chooses the most visually supported claim facet and decides whether evidence is supportive, contradictory, or insufficient.
4. `Risk layer`
   Adds `user_history_risk`, `manual_review_required`, `text_instruction_present`, or authenticity flags without changing clear visual truth.

## Claim Extraction Methodology

The default parser uses deterministic phrase matching so it remains stable and cheap. In a stronger deployment, the parser prompt in `prompts/claim_extraction.md` can be routed through an LLM for richer multilingual extraction.

It detects:

- claimed object type
- claimed damage type
- claimed object part
- explicit multi-part claims
- severity hints
- suspicious approval or instruction language

## Image Analysis Methodology

### Production path

Use `provider=openai` with a multimodal model such as `gpt-4o` or `gpt-4.1` vision-capable variants. Each image is reviewed independently using the prompt in `prompts/image_review.md`.

### Offline path

Use `provider=offline` for smoke tests when no API key is present. This mode can inspect image validity, simple quality signals, and OCR-detectable instruction text, but it is intentionally conservative and not intended for leaderboard submission.

## Fraud Detection Strategy

Fraud and integrity cues are modeled separately from claim truth:

- `text_instruction_present`: notes embedded in images or conversation trying to force approval
- `non_original_image`: watermarks, screenshots, stock-looking assets
- `possible_manipulation`: edited or suspicious imagery
- `claim_mismatch`: claimed part or issue differs from visible evidence
- `user_history_risk`: repeat exaggeration or mismatch history
- `manual_review_required`: escalation condition, not an automatic denial

## Evidence Verification Logic

The aggregator follows a conservative contract:

- `supported`: relevant part is visible and visible damage matches the claim
- `contradicted`: relevant part is visible but the claimed damage is absent or clearly different
- `not_enough_information`: relevant part is not visible clearly enough or images are unusable

## Confidence Scoring Design

Confidence is based on:

- support score from image assessments
- contradiction score from mismatching evidence
- completeness of the relevant object part view
- presence of authenticity and review risk flags

Low-confidence or suspicious cases should be escalated rather than overcommitted.

## Model Comparison Report

### GPT-4o

- Accuracy expectation: high for holistic multimodal reasoning
- Cost: medium to high
- Latency: medium
- Strengths: strong instruction following, good image-text grounding, good structured outputs
- Weaknesses: costlier than lightweight alternatives
- Recommended use: final adjudication or single-pass image review

### Gemini

- Accuracy expectation: high, especially on mixed media and OCR-heavy images
- Cost: medium
- Latency: medium
- Strengths: strong multimodal context windows, good OCR
- Weaknesses: structured consistency can vary by prompting
- Recommended use: image review and authenticity checks

### Claude

- Accuracy expectation: high for careful reasoning and justification quality
- Cost: medium to high
- Latency: medium
- Strengths: conservative reasoning and nuanced explanations
- Weaknesses: multimodal availability may depend on deployment path
- Recommended use: second-pass adjudication or judge-facing rationales

### Qwen-VL / InternVL / Llama Vision

- Accuracy expectation: medium to high depending on finetuning and hardware
- Cost: lower marginal inference cost when self-hosted
- Latency: variable, depends on GPU
- Strengths: controllable deployment and batching
- Weaknesses: weaker calibration, more engineering overhead, uneven OCR/authenticity detection
- Recommended use: cost-sensitive ensemble first pass

### Florence and other lightweight vision models

- Accuracy expectation: medium for object localization and captioning tasks
- Cost: low
- Latency: low
- Strengths: useful for cheap prefilters and object validation
- Weaknesses: weaker claim-level reasoning
- Recommended use: pre-screening, object presence checks, and routing

## Competition Strategy

For leaderboard optimization:

- run a cheap image-review pass first
- escalate low-confidence, contradictory, or fraud-flagged rows to a stronger model
- use self-consistency only for ambiguous rows
- keep prompts deterministic and schema-constrained
- cache image-level results aggressively
- avoid dataset-specific hardcoding

## Repository Structure

```text
code/
├── main.py
├── README.md
├── evaluation/
│   └── main.py
├── prompts/
│   ├── claim_extraction.md
│   ├── image_review.md
│   └── final_reasoning.md
├── tests/
│   ├── test_claim_parser.py
│   └── test_decision.py
└── claim_verifier/
    ├── __init__.py
    ├── claim_parser.py
    ├── config.py
    ├── decision.py
    ├── io_utils.py
    ├── metrics.py
    ├── pipeline.py
    ├── reporting.py
    ├── schemas.py
    └── providers/
        ├── __init__.py
        ├── base.py
        ├── offline.py
        └── openai_provider.py
```

## Running The System

### Offline smoke test

```bash
python /workspace/code/main.py --provider offline --claims /workspace/dataset/claims.csv --output /workspace/output.csv
```

### OpenAI production run

```bash
export OPENAI_API_KEY=YOUR_KEY
python /workspace/code/main.py --provider openai --model gpt-4o --claims /workspace/dataset/claims.csv --output /workspace/output.csv
```

### Evaluation

```bash
python /workspace/code/evaluation/main.py --provider openai --model gpt-4o
```

## Evaluation Framework

The evaluator reports:

- claim-status accuracy
- evidence-standard accuracy
- issue-type accuracy
- object-part accuracy
- severity accuracy
- macro F1 on claim status
- grounding overlap rate on supporting-image IDs
- confusion matrix

Recommended validation workflow:

1. Evaluate on `sample_claims.csv`.
2. Inspect contradictory and `not_enough_information` cases.
3. Compare prompts or model configurations.
4. Freeze the best configuration before scoring `claims.csv`.

## Error Analysis Framework

Slice failures into:

- wrong object
- wrong object part
- issue-type mismatch
- insufficient view quality
- non-original or manipulated imagery
- multilingual claim parsing errors
- multi-part claim compression errors

## Cost Analysis

For a hosted VLM, cost scales approximately with:

- number of images
- average prompt length
- number of escalation passes

The cheapest reliable pattern is:

- first-pass image review on every image
- second-pass adjudication only on low-confidence rows
- aggressive caching at the image level

## Performance Optimization Recommendations

- Cache image-level outputs by image bytes plus claim context.
- Parallelize per-image review within each claim.
- Deduplicate identical images across reruns.
- Use a stronger model only for ambiguous or suspicious rows.

## Deployment Strategy

- package as a CLI batch processor
- schedule evaluation before final test inference
- keep provider keys in environment variables only
- persist cached responses outside git artifacts when possible

## AI Judge Interview Preparation

Be ready to explain:

- why images are treated as the primary source of truth
- why claim parsing and image review are separate stages
- why user history is a risk feature rather than a decision override
- how contradiction differs from insufficient evidence
- how caching, escalation, and structured prompts reduce cost while preserving accuracy

Strong answer pattern:

1. describe the stage architecture
2. explain the conservative decision policy
3. show how fraud cues are separated from damage truth
4. reference evaluation metrics and ablations

## Risks And Mitigations

- Risk: stock or manipulated images
  Mitigation: watermark and instruction-text detection plus manual-review escalation
- Risk: multi-part claims collapsed into a single output row
  Mitigation: facet parsing and strongest-evidence selection
- Risk: poor OCR or low-light imagery
  Mitigation: separate quality flags and conservative `not_enough_information`
- Risk: overfitting to sample labels
  Mitigation: generic prompts, no file-specific rules, no hardcoded outputs

## Future Improvements

- add Gemini and Claude providers behind the same schema
- add OCR and segmentation-assisted preprocessing
- add model ensemble calibration and vote consistency
- add provider-based final adjudication prompt for complex multi-part claims
- add review queue integration for human escalation
