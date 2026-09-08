from langchain_core.prompts import PromptTemplate


SUMMARIZE_PROMPT = PromptTemplate.from_template(
"""You are an expert in clinical pharmacology.
Summarize the drug information below concisely while preserving all clinically meaningful content.

[Rules]
1. Keep the JSON key structure EXACTLY as given. Do not add, remove, or rename keys.
2. Keep "ingredient_name" unchanged. Copy it verbatim.
3. For the other fields, condense the text into a compact list of distinct, standardized medical terms.
   - Remove duplicates, marketing language, dosage details, and study citations.
   - Use standard clinical terminology (prefer generic disease/event names).
   - Do NOT invent information that is not present in the input.
   - Do NOT drop any distinct condition or event; merge only true synonyms.
4. Each summarized field must be a single string, with items separated by "; ".
5. If a field is empty or unknown, output an empty string "".

[Drug information]
{drug_info}

[Output format]
- Output ONLY a single JSON object.
- Format:
{{"ingredient_name": "...", "indications": "...", "mechanism_of_action": "...", "contraindications": "...", "adverse_effects": "..."}}
- Do NOT output any explanation, reasoning, preamble, code fences, or any other text.
"""
)