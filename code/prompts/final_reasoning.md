Aggregate the claim and image assessments into a final decision.

Reasoning rules:
- Images are the primary source of truth.
- Use conversation context only to define what should be validated.
- Use user history only as a risk layer; it must not override clear visual evidence.
- Separate observations from assumptions.
- If evidence is weak, contradictory, off-angle, or missing for the claimed part, prefer `not_enough_information`.
- Use `contradicted` when the claimed part is visible and the visible evidence does not support the reported damage.

Structured input:

{{REASONING_INPUT_JSON}}
