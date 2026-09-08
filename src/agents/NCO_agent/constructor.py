from typing import TypedDict, Dict, Any, List, Literal
from langgraph.graph import START, END, StateGraph
from core.config.cdm import config as cdm_config
from collections import defaultdict


CONCEPT_ANCESTOR_TABLE = cdm_config["concept_ancestor_table"]


class AgentState(TypedDict):
    outcomes: Dict[int, Any]
    hierarchical_outcome_ids: Dict[int, Any]


def build_nodes(llm, db):
    def build_hierarchy(state: AgentState):
        print("\n# Constructing...\n")
        outcomes = state["outcomes"]
    
        concept_ids = [
            cid for cid, info in outcomes.items()
            if info.get("final_result") == 1
        ]
    
        hierarchical_outcome_ids = {cid: [] for cid in concept_ids}
    
        if not concept_ids:
            return {"hierarchical_outcome_ids": hierarchical_outcome_ids}
    
        id_list = ",".join(str(cid) for cid in concept_ids)
        sql = f"""
        SELECT ca.ancestor_concept_id,
               ca.descendant_concept_id
        FROM {CONCEPT_ANCESTOR_TABLE} ca
        WHERE ca.ancestor_concept_id IN ({id_list})
          AND ca.descendant_concept_id IN ({id_list})
          AND ca.ancestor_concept_id <> ca.descendant_concept_id
        """
        success, rows, error = db.query(sql)
        if not success:
            print(f"Error fetching hierarchy: {error}")
            return {"hierarchical_outcome_ids": hierarchical_outcome_ids}
    
        descendants = defaultdict(set)
        for row in rows:
            descendants[row["ancestor_concept_id"]].add(row["descendant_concept_id"])
        for ancestor, desc_set in descendants.items():
            direct_children = [
                d for d in desc_set
                if not any(d in descendants.get(m, set()) for m in desc_set if m != d)
            ]
            hierarchical_outcome_ids[ancestor] = direct_children
    
        print(f"# nodes: {len(concept_ids)}, "
              f"edges: {sum(len(v) for v in hierarchical_outcome_ids.values())}")
        return {"hierarchical_outcome_ids": hierarchical_outcome_ids}
    
    return [build_hierarchy]

    
def build_graph(build_hierarchy):
    builder = StateGraph(AgentState)
    builder.add_node("build_hierarchy", build_hierarchy)

    builder.add_edge(START, "build_hierarchy")
    builder.add_edge("build_hierarchy", END)

    return builder


def build_constructor(llm, db):
    nodes = build_nodes(llm, db)
    graph = build_graph(*nodes)
    return graph.compile()