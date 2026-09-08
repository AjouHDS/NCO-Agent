from langchain_core.prompts import PromptTemplate


VALIDATE_PROMPT = PromptTemplate.from_template(
"""You are an expert in pharmacoepidemiology.

Your task is to judge whether the given outcome (disease/symptom/event) qualifies as a NEGATIVE CONTROL OUTCOME (NCO) for the given drug.

[What a negative control outcome is]
A negative control outcome is a result (disease/symptom/event) that has NO causal relationship with the drug. It is used to detect confounding or bias in observational studies. An outcome qualifies as a valid negative control ONLY IF it satisfies ALL of the following:
1. It is NOT an indication of the drug (not a condition the drug treats or prevents).
2. It is NOT a contraindication or a known adverse effect of the drug.
3. It has NO causal relationship through the drug's mechanism of action, metabolism, or pharmacokinetic/pharmacodynamic pathways. That is, there is no biological basis for this drug to cause or prevent the outcome.

If the outcome violates ANY of the three conditions, it is NOT a valid negative control.

[How to reason]
- The drug information provided below is REFERENCE ONLY. It is not an exhaustive or authoritative list.
- Do NOT conclude that there is no causal relationship simply because the outcome is absent from the drug information. Absence from the list is NOT evidence of no relationship.
- Base your judgment on your own expert knowledge of the drug's pharmacological mechanism, metabolism, pharmacokinetics/pharmacodynamics, and the pathophysiology of the outcome.
- Reason from the underlying biological mechanism linking (or not linking) the drug and the disease, using the provided information only as supporting context.

[Outcome Name]
{outcome_name}

[Drug informations (reference only)]
{drug_infos}

[Decision]
- result = 1 : the outcome IS a valid negative control (no causal relationship with the drug).
- result = 0 : the outcome is NOT a valid negative control (it is an indication, contraindication, adverse effect, or otherwise causally related).

[Output format]
- Output ONLY a single JSON object.
- Format: {{"result": 0, "reason": ""}}
- "reason" must be a complete sentence explaining the basis for the decision:
  - If result = 1, explain why there is no causal relationship, grounded in the drug's mechanism and the outcome's pathophysiology (not merely its absence from the reference information).
  - If result = 0, explain what the causal relationship is (e.g., the outcome is an indication / contraindication / adverse effect, or is mechanistically linked through a specific pathway).
- Do NOT output any explanation, reasoning, preamble, code fences, or any other text outside the JSON.
"""
)