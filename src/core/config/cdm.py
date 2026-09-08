from dotenv import load_dotenv
import os
load_dotenv() 


config = {
    "achilles_results": os.getenv("ACHILLES_RESULTS"),
    "concept_table": os.getenv("CONCEPT_TABLE"),
    "concept_ancestor_table": os.getenv("CONCEPT_ANCESTOR_TABLE"),
    "concept_relationship_table": os.getenv("CONCEPT_RELATIONSHIP_TABLE"),
    "condition_occurrence_table": os.getenv("CONDITION_OCCURRENCE_TABLE"),
    "person_count_with_descendants_path": "/workspace/workspace/workspace/data/person_count_with_descendants.csv",
}