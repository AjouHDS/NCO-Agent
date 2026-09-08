import os
import csv
import re
from core.config.cdm import config as cdm_config


ACHILLES_RESULTS = cdm_config["achilles_results"]
CONCEPT_TABLE = cdm_config["concept_table"]
CONCEPT_ANCESTOR_TABLE = cdm_config["concept_ancestor_table"]
CONDITION_OCCURRENCE_TABLE = cdm_config["condition_occurrence_table"]


exclude_words = [
    r"finding$",
    r"^Disorder of",
    r"^Finding of",
    r"^Disease of",
    r"Injury of",
    r"by site$",
    r"by body site$",
    r"by mechanism$",
    r"of body region$",
    r"of anatomical site$",
    r"of specific body structure$",
]
exception_words = ["due to", "caused by"]
exclude_pattern = re.compile("|".join(exclude_words))
exception_pattern = re.compile("|".join(exception_words))


def should_remove(name: str) -> bool:
    return bool(exclude_pattern.search(name)) and not exception_pattern.search(name)


def filter_concepts(names: list[str]) -> list[str]:
    return [n for n in names if not should_remove(n)]


def build_generate_sql(min_patients: int) -> str:
    # Aliases are set to concept_id / concept_name / patient_count so the
    # generated CSV columns line up with the loader below.
    return f"""
SELECT
    c.concept_id                 AS concept_id,
    c.concept_name               AS concept_name,
    COUNT(DISTINCT co.person_id) AS patient_count
FROM {CONCEPT_TABLE} c
JOIN {CONCEPT_ANCESTOR_TABLE} ca
  ON c.concept_id = ca.ancestor_concept_id
JOIN {CONDITION_OCCURRENCE_TABLE} co
  ON ca.descendant_concept_id = co.condition_concept_id
WHERE c.domain_id = 'Condition'
  AND c.standard_concept = 'S'
  AND c.invalid_reason IS NULL
GROUP BY
    c.concept_id,
    c.concept_name
HAVING
    COUNT(DISTINCT co.person_id) >= {min_patients}
ORDER BY
    patient_count DESC;
"""


def generate_person_count_with_descendants(db, min_patients, save_path):
    print(f"# generating person_count_with_descendants (min_patients={min_patients})...")
    outcomes = {}

    sql = build_generate_sql(min_patients)
    success, rows, error = db.query(sql)
    if not success:
        print(f"# error fetching concepts: {error}")
        return outcomes

    print(f"# fetched {len(rows)} concepts from database")

    for row in rows:
        name = row["concept_name"]
        if should_remove(name):  # skip parent/high-level concepts
            continue
        concept_id = int(row["concept_id"])
        outcomes[concept_id] = {
            "name": name,
            "patient_count": int(row["patient_count"]),
        }

    print(f"# {len(outcomes)} concepts kept after filtering")

    # save to /data/person_count_with_descendants.csv
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["concept_id", "concept_name", "patient_count"])
        for concept_id, info in outcomes.items():
            writer.writerow([concept_id, info["name"], info["patient_count"]])

    print(f"# saved to {save_path}")
    return outcomes


def load_person_count_with_descendants(db, min_patients, path):
    outcomes = {}

    # generate if the file is missing
    if not os.path.exists(path):
        print(f"# {path} not found")
        if db is None:
            print("# db is required to generate but was not provided")
            return outcomes
        return generate_person_count_with_descendants(db, min_patients, path)

    print(f"# loading from {path}")
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["concept_name"]
            if should_remove(name):  # skip parent/high-level concepts
                continue
            patient_count = int(row["patient_count"])
            if patient_count < min_patients:  # apply threshold on load as well
                continue
            concept_id = int(row["concept_id"])
            outcomes[concept_id] = {
                "name": name,
                "patient_count": patient_count,
            }

    print(f"# loaded {len(outcomes)} concepts (min_patients={min_patients})")
    return outcomes