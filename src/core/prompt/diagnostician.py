from langchain_core.prompts import PromptTemplate


DIAGNOSE_PROMPT = PromptTemplate.from_template(
"""You are evaluating whether a set of negative control outcome (NCO) candidates is sufficient for use in a study.

## Background
Negative control outcomes are conditions that are not causally related to the exposure of interest. They are used to detect residual confounding and systematic bias in observational studies. A good NCO set should be:

1. **Adequate in number** - Around 100 NCOs is a common target. This is a guideline, not a hard rule: a set somewhat below 100 may still be acceptable if it is otherwise strong, while a set that barely reaches 100 but is highly concentrated in one area may still be insufficient.
2. **Diverse in distribution** - NCOs should span a wide range of organ systems, disease types, and clinical domains. A set concentrated in a single body region or disease category (e.g. mostly skin conditions, or mostly one organ system) is poor even if numerous, because it cannot detect bias broadly.
3. **Sufficiently powered** - Each NCO needs enough patients to yield stable estimates. Outcomes with very low patient counts contribute little statistical signal. Consider whether a reasonable proportion of the candidates have adequate patient counts.

## NCO candidates
Total number of candidates: {nco_count}

Each entry below has a condition name and its patient count.

{nco_list}

## Your task
Assess whether this NCO set is sufficient for the study, or whether additional search for more candidates is needed. Weigh all three factors together — do not rely on count alone. Judge diversity from the condition names (what organ systems / disease categories they cover and whether any category dominates).

Respond with a JSON object in exactly this format:
{{"diagnostics": 1, "reason": ""}}

- Set "diagnostics" to 1 if the set is sufficient, or 0 if it is insufficient and more search is needed.
- In "reason", explain your judgment in either case: cite the count, describe the diversity of coverage (which categories are well represented and which are missing or overrepresented), and comment on patient-count adequacy. Keep it concise but specific.

Output only the JSON object, with no other text.
"""
)