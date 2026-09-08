from typing import TypedDict, Dict, Any, List, Literal
from langgraph.graph import START, END, StateGraph
from core.prompt.diagnostician import DIAGNOSE_PROMPT
from core.utils import parse_json_list, parse_json_dict
from core.config.cdm import config as cdm_config


MINIMUM_MIN_PATIENTS = 500


class AgentState(TypedDict):
    outcomes: Dict[int, Any]
    diagnostics: int
    min_patients: int
    step: int


def build_nodes(llm, db):
    
    def run_outcome_review(outcomes):
        target_items = {k: v for k, v in outcomes.items() if v.get("final_result") == 2}
        total_count = len(target_items)
    
        count_0 = sum(1 for v in outcomes.values() if v.get("final_result") == 0)
        count_1 = sum(1 for v in outcomes.values() if v.get("final_result") == 1)
    
        print(f"Current Status - Excluded (0): {count_0}, Included (1): {count_1}, Pending Review (2): {total_count}")
    
        if total_count == 0:
            print("No pending concepts to review.")
            return outcomes
    
        while True:
            print("\nSelect a mode:")
            print("1. Include All")
            print("2. Exclude All")
            print("3. Follow LLM Review")
            print("4. Individual Review")
            
            # user_input = input("Choose a mode (1-3): ").strip()
            user_input = "3"
            
            if not user_input.isdigit():
                print("Invalid input. Please enter a number (1, 2, or 3).\n")
                continue
    
            mode = int(user_input)
    
            if mode == 1:
                for concept_id in target_items:
                    outcomes[concept_id]["final_result"] = 1
                print("\nAll pending items have been set to Include (1).")
                break
    
            elif mode == 2:
                for concept_id in target_items:
                    outcomes[concept_id]["final_result"] = 0
                print("\nAll pending items have been set to Exclude (0).")
                break

            elif mode == 3:
                include_by_llm_count = 0
                for concept_id in target_items:
                    if outcomes[concept_id]["llm_validate_result"]["result"] == 1:
                        include_by_llm_count += 1
                    outcomes[concept_id]["final_result"] = outcomes[concept_id]["llm_validate_result"]["result"]
                print(f"\n {include_by_llm_count} of {total_count} included")
                break
                
            elif mode == 4:
                for now_concept_number, (concept_id, info) in enumerate(target_items.items(), start=1):
                    print(f"\n----------------------------------------")
                    print(f"[{now_concept_number}/{total_count}] Concept ID: {concept_id}")
                    print("name:", info["name"])
                    print("cem_result:", info["cem_result"])
                    print("llm_result:", info["llm_validate_result"]["result"])
                    print("llm_reason:", info["llm_validate_result"]["reason"])
                    print()
                    
                    while True:
                        review_input = input("Enter decision (0: Exclude, 1: Include): ").strip()
                        if review_input in ["0", "1"]:
                            outcomes[concept_id]["final_result"] = int(review_input)
                            break
                        print("Invalid input. Please enter either 0 or 1.")
    
                print("\nIndividual review completed.")
                break
    
            else:
                print("Out of range. Please choose a number between 1 and 4.\n")
    
        return outcomes
        
    def review_by_human(state: AgentState):
        print("\n# Human-in-the-Loop...\n")
        outcomes = state["outcomes"]
        updated_outcomes = run_outcome_review(outcomes)
        
        return {
            "outcomes": updated_outcomes
        }
    
    def diagnose(state: AgentState):
        print("\n# Diagnosing...\n")
        outcomes = state["outcomes"]
        min_patients = state["min_patients"]
        step = state["step"]

        nco_list = []
        for concept_id, info in outcomes.items():
            if info["final_result"] == 1:
                nco_list.append({"name": info["name"], "patient_count": info["patient_count"]})

        print(f"# Final total NCO count (min_patients={min_patients}): {len(nco_list)}")
        nco_text = "\n".join(
            f"- {item['name']} (n={item['patient_count']})"
            for item in nco_list
        )
        
        response = llm.invoke(DIAGNOSE_PROMPT, {"nco_count": len(nco_list), "nco_list": nco_text})
        response = parse_json_dict(response)

        diagnostics = response["diagnostics"]
        reason = response["reason"]
        print(f"# diagnostics: {diagnostics}")
        print(f"# reason: {reason}")
        min_patients -= step

        # 테스트용
        diagnostics = 0
        if diagnostics == 0 and min_patients < MINIMUM_MIN_PATIENTS:
            diagnostics = 1
            print("Stopping: search exhausted but criteria not fully met")
        elif diagnostics == 0:
            print("Insufficient: continuing with additional search")
        else:
            print("Sufficient")
    
        return {
            "diagnostics": diagnostics,
            "min_patients": min_patients,
        }

    return review_by_human, diagnose


def build_graph(review_by_human, diagnose):
    builder = StateGraph(AgentState)
    builder.add_node("review_by_human", review_by_human)
    builder.add_node("diagnose", diagnose)
    builder.add_edge(START, "review_by_human")
    builder.add_edge("review_by_human", "diagnose")
    builder.add_edge("diagnose", END)
    return builder


def build_diagnostician(llm, db):
    nodes = build_nodes(llm, db)
    graph = build_graph(*nodes)
    return graph.compile()