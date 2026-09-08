from typing import TypedDict, Dict, Any, List, Literal
from langgraph.graph import START, END, StateGraph
from core.prompt.suggestor import VALIDATE_PROMPT
from core.utils import parse_json_dict
from core.cem import get_negative_controls
from core.concept_pool import load_person_count_with_descendants
from core.config.cdm import config as cdm_config
import json
from pathlib import Path
from tqdm import tqdm


ACHILLES_RESULTS = cdm_config["achilles_results"]
CONCEPT_TABLE = cdm_config["concept_table"]
PERSON_COUNT_WITH_DESCENDANTS_PATH = cdm_config["person_count_with_descendants_path"]


class AgentState(TypedDict):
    ingredient_concept_ids: List
    ingredient_concepts: Dict[int, Any]
    outcomes: Dict[int, Any]
    cem_result: Dict[int, Any]

    min_patients: int

    
def is_valid_result(result):
    return (
        isinstance(result, dict)
        and "result" in result
        and "reason" in result
    )

    
def build_nodes(llm, db):

    def get_candidate_concepts(state: AgentState):
        print(f"# suggesting...")
        min_patients = state["min_patients"]

        outcomes = state.get("outcomes", {})
        loaded_outcomes = load_person_count_with_descendants(db, min_patients, PERSON_COUNT_WITH_DESCENDANTS_PATH)
        new_outcome_count = 0
        for concept_id, outcome_info in loaded_outcomes.items():
            if concept_id not in outcomes:
                outcomes[concept_id] = outcome_info
                new_outcome_count += 1
        print(f"# new outcome count: {new_outcome_count}")
                
        return {"outcomes": outcomes}
        
    def add_cem_result(state: AgentState): 
        outcomes = state["outcomes"]
        ingredient_concept_ids = state["ingredient_concept_ids"]

        
        if not state.get("cem_result"):
            print("# [CREATE] Generating cem_result...")
            cem_result = get_negative_controls(ingredient_concept_ids)
        else:
            print("# [SKIP] cem_result already created, skipping")
            cem_result = state["cem_result"]

        count = [0,0,0]
        
        for concept_id in outcomes.keys():
            if concept_id in cem_result:
                outcomes[concept_id]["cem_result"] = cem_result[concept_id]
            else:
                outcomes[concept_id]["cem_result"] = 2
            count[outcomes[concept_id]["cem_result"]]+=1
            
        print(f"# cem result count: {count}")
        return {
            "outcomes": outcomes,
            "cem_result": cem_result
        }

    
    def validate(state: AgentState):
        outcomes = state["outcomes"]
        ingredient_concepts = state["ingredient_concepts"]
        drug_infos = list(ingredient_concepts.values())
    
        pbar = tqdm(outcomes.items(), desc="Validating", unit="outcome")
        for concept_id, outcome_info in pbar:
            # Skip already-processed items (bar advances quickly)
            if "llm_validate_result" in outcomes[concept_id]:
                continue
    
            # Show the current item name next to the bar (truncate if long)
            pbar.set_postfix_str(outcome_info["name"][:30])
    
            max_retries = 3
            result = None
            for attempt in range(max_retries):
                try:
                    response = llm.invoke(
                        VALIDATE_PROMPT,
                        {"outcome_name": outcome_info["name"], "drug_infos": drug_infos},
                    )
                    result = parse_json_dict(response)
                    if is_valid_result(result):
                        break
                except Exception as e:
                    tqdm.write(f"[{concept_id}] attempt {attempt+1}/{max_retries} error: {e}")
                    result = None
    
            if not is_valid_result(result):
                tqdm.write(f"[{concept_id}] max retries exceeded — validation failed")
                result = {"result": None, "reason": "validation_failed_after_retries"}
    
            outcomes[concept_id]["llm_validate_result"] = result
            cem_result = outcomes[concept_id]["cem_result"]
            llm_validate_result = outcomes[concept_id]["llm_validate_result"]["result"]
    
            if cem_result == llm_validate_result and cem_result in (0, 1):
                outcomes[concept_id]["final_result"] = cem_result
            else:
                outcomes[concept_id]["final_result"] = 2
    
        return {"outcomes": outcomes}
    return get_candidate_concepts, add_cem_result, validate

    
def build_graph(get_candidate_concepts, add_cem_result, validate):
    builder = StateGraph(AgentState)
    builder.add_node("get_candidate_concepts", get_candidate_concepts)
    builder.add_node("add_cem_result", add_cem_result)
    builder.add_node("validate", validate)

    builder.add_edge(START, "get_candidate_concepts")
    builder.add_edge("get_candidate_concepts", "add_cem_result")
    builder.add_edge("add_cem_result", "validate")
    builder.add_edge("validate", END)

    return builder


def build_suggestor(llm, db):
    get_candidate_concepts, add_cem_result, validate = build_nodes(llm, db)
    graph = build_graph(get_candidate_concepts, add_cem_result, validate)
    return graph.compile()