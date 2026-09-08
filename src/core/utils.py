from pathlib import Path
import json


def parse_json_dict(text):
    try:
        clean_text = text.strip().replace("```json", "").replace("```", "")
        data = json.loads(clean_text)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError, Exception):
        return {}


def parse_json_list(text):
    try:
        clean_text = text.strip().replace("```json", "").replace("```", "")
        data = json.loads(clean_text)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError, Exception):
        return []


def get_descendant_concept_ids(db, concept_ids, batch_size: int = 1000):
    if not concept_ids:
        return []

    safe_ids = [int(cid) for cid in concept_ids]
    result: set[int] = set() 

    for i in range(0, len(safe_ids), batch_size):
        chunk = safe_ids[i : i + batch_size]
        id_list = ", ".join(str(cid) for cid in chunk)

        sql = f"""
        SELECT DISTINCT c.concept_id
        FROM [MIMIC3_CDM].[dbo].[concept_ancestor] ca
        JOIN [MIMIC3_CDM].[dbo].[concept] c
            ON ca.descendant_concept_id = c.concept_id
        WHERE ca.ancestor_concept_id IN ({id_list})
            AND c.standard_concept = 'S'
            AND c.invalid_reason = 'n'
        """

        success, rows, error = db.query(sql)
        if not success:
            print(f"# Error (batch {i // batch_size}): {error}")
            continue

        for r in rows:
            result.add(r["concept_id"]) 

    ids = list(result)
    return ids